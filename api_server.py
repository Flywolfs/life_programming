from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from income_tax_calculator import (
    load_config,
    calculate_5year_savings,
    calculate_staged_savings,
)


app = FastAPI(title="跨境生活储蓄分析系统")

# 允许前端在本机直接访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载前端静态文件目录: frontend/ -> /static
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# ==== Pydantic 模型定义 ====


class StageConfig(BaseModel):
    scenario: str
    years: float
    custom_costs: Optional[dict] = None


class StagedSavingsRequest(BaseModel):
    annual_salary_hkd: float
    stages: List[StageConfig]
    mpf_annual: float = 18000
    social_insurance_annual: float = 21312


class SensitivityRequest(BaseModel):
    annual_salary_hkd: float
    years: float = 5
    scenario: str  # '香港工作_香港生活' 或 '香港工作_内地生活'
    varied_item: str  # 例如: '房租_月'
    start: float
    end: float
    step: float
    mpf_annual: float = 18000
    social_insurance_annual: float = 21312


class LifestyleCompareRequest(BaseModel):
    annual_salary_hkd: float
    years: float = 5
    hk_varied_item: str = "房租_月"  # 香港场景变化的消费项
    hk_start: float
    hk_end: float
    hk_step: float
    cn_varied_item: str = "房租_月"  # 内地场景变化的消费项
    cn_start: float
    cn_end: float
    cn_step: float
    mpf_annual: float = 18000
    social_insurance_annual: float = 21312


# ==== 配置相关 API ====


@app.get("/api/config")
def get_config():
    """获取当前 tax_config.json 配置"""
    return load_config()


@app.post("/api/config")
def save_config(config: dict):
    """保存配置到 tax_config.json"""
    import json
    import os

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "tax_config.json")

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {e}")

    return {"status": "ok"}


# ==== 模块一: 分阶段生活配置与储蓄计算 ====


@app.post("/api/staged-savings")
def api_staged_savings(req: StagedSavingsRequest):
    """根据前端提供的阶段配置,计算分阶段储蓄结果"""
    config = load_config()

    stages = [s.dict() for s in req.stages]
    result = calculate_staged_savings(
        annual_salary_hkd=req.annual_salary_hkd,
        stages=stages,
        config=config,
        mpf_annual=req.mpf_annual,
        social_insurance_annual=req.social_insurance_annual,
    )
    return result


# ==== 模块二: 单一消费项敏感性分析 ====


@app.post("/api/sensitivity")
def api_sensitivity(req: SensitivityRequest):
    """分析单一消费项(如房租)变化对总储蓄的影响"""
    config = load_config()
    base_config = config

    life_cost_config = base_config.get("生活成本配置", {})
    if req.scenario not in life_cost_config:
        raise HTTPException(status_code=400, detail=f"未知生活场景: {req.scenario}")

    exchange_rate = base_config.get("港币兑人民币汇率", 0.9)

    values = []
    savings_cny = []

    current = req.start
    # 防止死循环
    direction = 1 if req.end >= req.start else -1

    while (direction == 1 and current <= req.end) or (direction == -1 and current >= req.end):
        # 构造临时配置,覆写对应消费项
        tmp_config = base_config.copy()
        tmp_life = tmp_config.get("生活成本配置", {}).copy()
        scenario_conf = tmp_life.get(req.scenario, {}).copy()
        scenario_conf[req.varied_item] = current
        tmp_life[req.scenario] = scenario_conf
        tmp_config["生活成本配置"] = tmp_life

        result = calculate_5year_savings(
            annual_salary_hkd=req.annual_salary_hkd,
            years=req.years,
            scenarios=[req.scenario],
            config=tmp_config,
            mpf_annual=req.mpf_annual,
            social_insurance_annual=req.social_insurance_annual,
        )
        data = result[req.scenario]

        total_savings = data[f"{req.years}年累计储蓄"]
        currency = data["货币单位"]
        if currency == "HKD":
            total_savings_cny = total_savings * exchange_rate
        else:
            total_savings_cny = total_savings

        values.append(current)
        savings_cny.append(round(total_savings_cny, 2))

        current = round(current + req.step * direction, 6)

    return {
        "scenario": req.scenario,
        "varied_item": req.varied_item,
        "values": values,
        "savings_cny": savings_cny,
        "annual_salary_hkd": req.annual_salary_hkd,
        "years": req.years,
    }


# ==== 模块三: 两地生活对比与交叉点识别 ====


@app.post("/api/lifestyle-cross-over")
def api_lifestyle_cross_over(req: LifestyleCompareRequest):
    """比较香港生活 vs 内地生活，横轴为累计储蓄，两个纵轴分别为两地消费项金额"""
    base_config = load_config()
    exchange_rate = base_config.get("港币兑人民币汇率", 0.9)

    scenarios = ["香港工作_香港生活", "香港工作_内地生活"]
    life_cost_config = base_config.get("生活成本配置", {})
    for s in scenarios:
        if s not in life_cost_config:
            raise HTTPException(status_code=400, detail=f"配置中缺少生活场景: {s}")

    # 香港场景: 遍历消费项变化范围
    hk_costs = []
    hk_savings = []
    current = req.hk_start
    direction = 1 if req.hk_end >= req.hk_start else -1

    while (direction == 1 and current <= req.hk_end) or (
        direction == -1 and current >= req.hk_end
    ):
        tmp_config = base_config.copy()
        tmp_life = tmp_config.get("生活成本配置", {}).copy()
        hk_conf = tmp_life.get("香港工作_香港生活", {}).copy()
        hk_conf[req.hk_varied_item] = current
        tmp_life["香港工作_香港生活"] = hk_conf
        tmp_config["生活成本配置"] = tmp_life

        result = calculate_5year_savings(
            annual_salary_hkd=req.annual_salary_hkd,
            years=req.years,
            scenarios=["香港工作_香港生活"],
            config=tmp_config,
            mpf_annual=req.mpf_annual,
            social_insurance_annual=req.social_insurance_annual,
        )

        hk_data = result["香港工作_香港生活"]
        hk_total = hk_data[f"{req.years}年累计储蓄"]
        hk_cny = hk_total * exchange_rate if hk_data["货币单位"] == "HKD" else hk_total

        hk_costs.append(current)
        hk_savings.append(round(hk_cny, 2))
        current = round(current + req.hk_step * direction, 6)

    # 内地场景: 遍历消费项变化范围
    cn_costs = []
    cn_savings = []
    current = req.cn_start
    direction = 1 if req.cn_end >= req.cn_start else -1

    while (direction == 1 and current <= req.cn_end) or (
        direction == -1 and current >= req.cn_end
    ):
        tmp_config = base_config.copy()
        tmp_life = tmp_config.get("生活成本配置", {}).copy()
        cn_conf = tmp_life.get("香港工作_内地生活", {}).copy()
        cn_conf[req.cn_varied_item] = current
        tmp_life["香港工作_内地生活"] = cn_conf
        tmp_config["生活成本配置"] = tmp_life

        result = calculate_5year_savings(
            annual_salary_hkd=req.annual_salary_hkd,
            years=req.years,
            scenarios=["香港工作_内地生活"],
            config=tmp_config,
            mpf_annual=req.mpf_annual,
            social_insurance_annual=req.social_insurance_annual,
        )

        cn_data = result["香港工作_内地生活"]
        cn_total = cn_data[f"{req.years}年累计储蓄"]
        cn_cny = cn_total * exchange_rate if cn_data["货币单位"] == "HKD" else cn_total

        cn_costs.append(current)
        cn_savings.append(round(cn_cny, 2))
        current = round(current + req.cn_step * direction, 6)

    # 查找交叉点: 在相同的储蓄水平下，两地消费项的交叉
    # 先找到共同的储蓄范围
    hk_savings_min = min(hk_savings)
    hk_savings_max = max(hk_savings)
    cn_savings_min = min(cn_savings)
    cn_savings_max = max(cn_savings)

    overlap_min = max(hk_savings_min, cn_savings_min)
    overlap_max = min(hk_savings_max, cn_savings_max)

    cross_point = None
    dominant = None

    if overlap_max >= overlap_min:
        # 有重叠区间，在这个区间内查找交叉点
        # 对于每个储蓄值，插值计算对应的消费项金额
        def interpolate_cost(savings_list, cost_list, target_saving):
            """https://en.wikipedia.org/wiki/Linear_interpolation"""
            for i in range(len(savings_list) - 1):
                s1, s2 = savings_list[i], savings_list[i + 1]
                c1, c2 = cost_list[i], cost_list[i + 1]
                if min(s1, s2) <= target_saving <= max(s1, s2):
                    if s2 != s1:
                        ratio = (target_saving - s1) / (s2 - s1)
                        return c1 + (c2 - c1) * ratio
                    else:
                        return c1
            return None

        # 在重叠区间内采样，查找交叉点
        sample_step = (overlap_max - overlap_min) / 100
        prev_diff = None
        prev_saving = None
        prev_hk_cost = None
        prev_cn_cost = None

        for i in range(101):
            target_saving = overlap_min + i * sample_step
            hk_cost = interpolate_cost(hk_savings, hk_costs, target_saving)
            cn_cost = interpolate_cost(cn_savings, cn_costs, target_saving)

            if hk_cost is not None and cn_cost is not None:
                diff = hk_cost - cn_cost
                if prev_diff is not None and prev_diff * diff <= 0:
                    # 发现交叉
                    if prev_saving != target_saving:
                        ratio = abs(prev_diff) / (abs(prev_diff) + abs(diff))
                        cross_saving = prev_saving + (target_saving - prev_saving) * ratio
                        cross_hk_cost = prev_hk_cost + (hk_cost - prev_hk_cost) * ratio
                        cross_cn_cost = prev_cn_cost + (cn_cost - prev_cn_cost) * ratio
                        cross_point = {
                            "saving_cny": round(cross_saving, 2),
                            "hk_cost": round(cross_hk_cost, 2),
                            "cn_cost": round(cross_cn_cost, 2),
                        }
                    break
                prev_diff = diff
                prev_saving = target_saving
                prev_hk_cost = hk_cost
                prev_cn_cost = cn_cost

    # 判断优势
    if cross_point is None:
        # 没有交叉点，判断哪种方式更优
        # 比较在相同消费水平下的储蓄
        if hk_savings_min > cn_savings_max:
            dominant = "香港生活更优（相同消费下储蓄更多）"
        elif cn_savings_min > hk_savings_max:
            dominant = "内地生活更优（相同消费下储蓄更多）"
        elif overlap_max >= overlap_min:
            # 有重叠但无交叉，比较在相同储蓄下的消费
            mid_saving = (overlap_min + overlap_max) / 2
            
            def interpolate_cost(savings_list, cost_list, target_saving):
                for i in range(len(savings_list) - 1):
                    s1, s2 = savings_list[i], savings_list[i + 1]
                    c1, c2 = cost_list[i], cost_list[i + 1]
                    if min(s1, s2) <= target_saving <= max(s1, s2):
                        if s2 != s1:
                            ratio = (target_saving - s1) / (s2 - s1)
                            return c1 + (c2 - c1) * ratio
                        else:
                            return c1
                return None
            
            hk_cost_mid = interpolate_cost(hk_savings, hk_costs, mid_saving)
            cn_cost_mid = interpolate_cost(cn_savings, cn_costs, mid_saving)
            
            if hk_cost_mid is not None and cn_cost_mid is not None:
                if hk_cost_mid < cn_cost_mid:
                    dominant = "香港生活更优（相同储蓄下消费更低）"
                else:
                    dominant = "内地生活更优（相同储蓄下消费更低）"

    return {
        "hk_costs": hk_costs,
        "hk_savings": hk_savings,
        "cn_costs": cn_costs,
        "cn_savings": cn_savings,
        "cross_point": cross_point,
        "dominant": dominant,
        "hk_varied_item": req.hk_varied_item,
        "cn_varied_item": req.cn_varied_item,
        "annual_salary_hkd": req.annual_salary_hkd,
        "years": req.years,
    }
