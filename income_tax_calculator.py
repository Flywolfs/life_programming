"""
香港和中国大陆工资收入税费计算器
支持自定义扣除项配置
"""
import json
import os


def load_config(config_file='tax_config.json'):
    """
    加载税务配置文件
    
    参数:
        config_file: 配置文件路径
    
    返回:
        dict: 配置信息
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, config_file)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"配置文件 {config_file} 不存在,使用默认配置")
        return {}


def calculate_hk_deductions(config):
    """
    根据配置计算香港薪俸税可扣除金额
    
    参数:
        config: 香港扣除配置
    
    返回:
        tuple: (总扣除额, 扣除明细)
    """
    deductions = {}
    total = 0
    
    # 加载标准扣除额度
    all_config = load_config()
    standard = all_config.get('香港薪俸税扣除项', {})
    
    # 基本免税额或已婚人士免税额
    if config.get('婚姻状况') == '已婚':
        amount = standard.get('已婚人士免税额', 264000)
        deductions['已婚人士免税额'] = amount
        total += amount
    else:
        amount = standard.get('基本免税额', 132000)
        deductions['基本免税额'] = amount
        total += amount
    
    # 子女免税额
    children = config.get('子女数量', 0)
    if children > 0:
        child_allowance = standard.get('子女免税额_每名', 120000) * children
        deductions['子女免税额'] = child_allowance
        total += child_allowance
        
        # 出生年度额外免税额
        if config.get('今年有新生儿', False):
            newborn_allowance = standard.get('子女免税额_每名_出生年度额外', 120000)
            deductions['新生儿额外免税额'] = newborn_allowance
            total += newborn_allowance
    
    # 供养兄弟姊妹
    siblings = config.get('供养兄弟姊妹', 0)
    if siblings > 0:
        amount = standard.get('供养兄弟姊妹免税额_每名', 37500) * siblings
        deductions['供养兄弟姊妹免税额'] = amount
        total += amount
    
    # 供养父母
    parents_config = config.get('供养父母', {})
    parent_rates = standard.get('供养父母及供养祖父母或外祖父母免税额', {})
    
    for key, value in parents_config.items():
        if value:
            if '60岁以上_同住' in key:
                amount = parent_rates.get('60岁以上_同住', 50000)
                deductions[f'供养父母_{key}'] = amount
                total += amount
            elif '60岁以上_不同住' in key:
                amount = parent_rates.get('60岁以上_不同住', 25000)
                deductions[f'供养父母_{key}'] = amount
                total += amount
            elif '55-59岁_同住' in key:
                amount = parent_rates.get('55-59岁_同住', 25000)
                deductions[f'供养父母_{key}'] = amount
                total += amount
            elif '55-59岁_不同住' in key:
                amount = parent_rates.get('55-59岁_不同住', 12500)
                deductions[f'供养父母_{key}'] = amount
                total += amount
    
    # 单亲免税额
    if config.get('是否单亲', False):
        amount = standard.get('单亲免税额', 132000)
        deductions['单亲免税额'] = amount
        total += amount
    
    # 伤残受养人
    disabled = config.get('伤残受养人数', 0)
    if disabled > 0:
        amount = standard.get('伤残受养人免税额', 75000) * disabled
        deductions['伤残受养人免税额'] = amount
        total += amount
    
    # 个人进修开支
    education = config.get('个人进修开支', 0)
    if education > 0:
        max_education = standard.get('个人进修开支_最高', 100000)
        amount = min(education, max_education)
        deductions['个人进修开支'] = amount
        total += amount
    
    # 强制性公积金
    mpf = config.get('强制性公积金', 0)
    if mpf > 0:
        max_mpf = standard.get('强制性公积金计划_最高', 18000)
        amount = min(mpf, max_mpf)
        deductions['强制性公积金'] = amount
        total += amount
    
    # 认可退休计划
    retirement = config.get('认可退休计划', 0)
    if retirement > 0:
        max_retirement = standard.get('认可退休计划_最高', 18000)
        amount = min(retirement, max_retirement)
        deductions['认可退休计划'] = amount
        total += amount
    
    # 居所贷款利息
    mortgage = config.get('居所贷款利息', 0)
    if mortgage > 0:
        max_mortgage = standard.get('居所贷款利息_最高', 100000)
        amount = min(mortgage, max_mortgage)
        deductions['居所贷款利息'] = amount
        total += amount
    
    # 自愿医保
    vhis = config.get('自愿医保人数', 0)
    if vhis > 0:
        max_per_person = standard.get('自愿医保保费_最高_每人', 8000)
        amount = vhis * max_per_person
        deductions['自愿医保保费'] = amount
        total += amount
    
    # 合资格年金保费
    annuity = config.get('合资格年金保费', 0)
    if annuity > 0:
        max_annuity = standard.get('合资格年金保费_最高', 60000)
        amount = min(annuity, max_annuity)
        deductions['合资格年金保费'] = amount
        total += amount
    
    # 住宅租金
    rent = config.get('住宅租金', 0)
    if rent > 0:
        max_rent = standard.get('住宅租金_最高', 100000)
        amount = min(rent, max_rent)
        deductions['住宅租金'] = amount
        total += amount
    
    return total, deductions


def calculate_hk_salary_tax(annual_income, use_config=True, config=None):
    """
    计算香港薪俸税
    
    香港采用两级税制:
    1. 累进税率制 (Progressive Tax Rates)
    2. 标准税率制 (Standard Tax Rate) - 15%
    取两者中较低的税额
    
    参数:
        annual_income: 年度总收入 (港币)
        use_config: 是否使用配置文件中的扣除项
        config: 自定义配置(如不提供则从配置文件读取)
    
    返回:
        dict: 包含应缴税额、适用税制等详细信息
    """
    # 计算总扣除额
    total_deductions = 0
    deduction_details = {}
    
    if use_config:
        if config is None:
            all_config = load_config()
            config = all_config.get('我的扣除配置_香港', {})
        total_deductions, deduction_details = calculate_hk_deductions(config)
    else:
        # 默认只使用基本免税额
        total_deductions = 132000
        deduction_details = {'基本免税额': 132000}
    
    # 累进税率表 (2024/25年度)
    PROGRESSIVE_RATES = [
        (50000, 0.02),    # 首 $50,000 按 2%
        (50000, 0.06),    # 次 $50,000 按 6%
        (50000, 0.10),    # 再 $50,000 按 10%
        (50000, 0.14),    # 再 $50,000 按 14%
        (float('inf'), 0.17)  # 余额按 17%
    ]
    
    # 标准税率
    STANDARD_RATE = 0.15
    
    # 计算应课税入息 (扣除所有免税额)
    taxable_income = max(0, annual_income - total_deductions)
    
    # 方法1: 累进税率计算
    progressive_tax = 0
    remaining_income = taxable_income
    
    for bracket_amount, rate in PROGRESSIVE_RATES:
        if remaining_income <= 0:
            break
        taxable_in_bracket = min(remaining_income, bracket_amount)
        progressive_tax += taxable_in_bracket * rate
        remaining_income -= taxable_in_bracket
    
    # 方法2: 标准税率计算 (扣除免税额后的收入)
    standard_tax = taxable_income * STANDARD_RATE
    
    # 取较低的税额
    final_tax = min(progressive_tax, standard_tax)
    tax_method = "累进税率" if progressive_tax < standard_tax else "标准税率"
    
    return {
        "年度总收入": annual_income,
        "总扣除额": total_deductions,
        "扣除明细": deduction_details,
        "应课税入息": taxable_income,
        "累进税率计算": round(progressive_tax, 2),
        "标准税率计算": round(standard_tax, 2),
        "应缴税额": round(final_tax, 2),
        "适用税制": tax_method,
        "实际税率": round(final_tax / annual_income * 100, 2) if annual_income > 0 else 0,
        "税后收入": round(annual_income - final_tax, 2)
    }


def calculate_mainland_deductions(config):
    """
    根据配置计算中国大陆个税可扣除金额
    
    参数:
        config: 大陆扣除配置
    
    返回:
        tuple: (总扣除额, 扣除明细)
    """
    deductions = {}
    total = 0
    
    # 加载标准扣除额度
    all_config = load_config()
    standard = all_config.get('中国大陆个税扣除项', {})
    
    # 基本减除费用
    basic = standard.get('基本减除费用', 60000)
    deductions['基本减除费用'] = basic
    total += basic
    
    # 专项扣除 (社保公积金)
    monthly_salary = config.get('月工资', 0)
    special_config = config.get('专项扣除', {})
    special_standard = standard.get('专项扣除', {})
    
    # 养老保险
    pension = special_config.get('养老保险_自定义')
    if pension is None and monthly_salary > 0:
        pension = monthly_salary * 12 * special_standard.get('养老保险_比例', 0.08)
    if pension:
        deductions['养老保险'] = round(pension, 2)
        total += pension
    
    # 医疗保险
    medical = special_config.get('医疗保险_自定义')
    if medical is None and monthly_salary > 0:
        medical = monthly_salary * 12 * special_standard.get('医疗保险_比例', 0.02)
    if medical:
        deductions['医疗保险'] = round(medical, 2)
        total += medical
    
    # 失业保险
    unemployment = special_config.get('失业保险_自定义')
    if unemployment is None and monthly_salary > 0:
        unemployment = monthly_salary * 12 * special_standard.get('失业保险_比例', 0.005)
    if unemployment:
        deductions['失业保险'] = round(unemployment, 2)
        total += unemployment
    
    # 住房公积金
    housing_fund = special_config.get('住房公积金_自定义')
    if housing_fund is None and monthly_salary > 0:
        # 考虑缴存基数上限
        max_base = special_standard.get('住房公积金_最高基数', 33891)
        base = min(monthly_salary, max_base)
        housing_fund = base * 12 * special_standard.get('住房公积金_比例', 0.12)
    if housing_fund:
        deductions['住房公积金'] = round(housing_fund, 2)
        total += housing_fund
    
    # 专项附加扣除
    additional_config = config.get('专项附加扣除', {})
    additional_standard = standard.get('专项附加扣除', {})
    
    # 子女教育
    children_edu = additional_config.get('子女教育_子女数', 0)
    if children_edu > 0:
        amount = children_edu * additional_standard.get('子女教育_每名', 12000)
        deductions['子女教育'] = amount
        total += amount
    
    # 继续教育
    if additional_config.get('继续教育_学历', False):
        amount = additional_standard.get('继续教育_学历', 4800)
        deductions['继续教育_学历'] = amount
        total += amount
    
    if additional_config.get('继续教育_职业资格', False):
        amount = additional_standard.get('继续教育_职业资格', 3600)
        deductions['继续教育_职业资格'] = amount
        total += amount
    
    # 大病医疗
    medical_expense = additional_config.get('大病医疗', 0)
    if medical_expense > 0:
        threshold = additional_standard.get('大病医疗_起付线', 15000)
        max_medical = additional_standard.get('大病医疗_最高', 80000)
        if medical_expense > threshold:
            amount = min(medical_expense - threshold, max_medical)
            deductions['大病医疗'] = amount
            total += amount
    
    # 住房贷款利息
    mortgage = additional_config.get('住房贷款利息', 0)
    if mortgage > 0:
        max_mortgage = additional_standard.get('住房贷款利息_最高', 12000)
        amount = min(mortgage, max_mortgage)
        deductions['住房贷款利息'] = amount
        total += amount
    
    # 住房租金
    rent = additional_config.get('住房租金', 0)
    if rent > 0:
        deductions['住房租金'] = rent
        total += rent
    
    # 赡养老人
    elderly = additional_config.get('赡养老人', 0)
    if elderly > 0:
        deductions['赡养老人'] = elderly
        total += elderly
    
    # 3岁以下婴幼儿照护
    infant = additional_config.get('3岁以下婴幼儿照护_子女数', 0)
    if infant > 0:
        amount = infant * additional_standard.get('3岁以下婴幼儿照护_每名', 12000)
        deductions['3岁以下婴幼儿照护'] = amount
        total += amount
    
    # 其他扣除
    other_config = config.get('其他扣除', {})
    other_standard = standard.get('其他扣除', {})
    
    # 年金
    annuity = other_config.get('年金', 0)
    if annuity > 0:
        max_annuity = other_standard.get('年金_最高', 12000)
        amount = min(annuity, max_annuity)
        deductions['年金'] = amount
        total += amount
    
    # 商业健康保险
    commercial_health = other_config.get('商业健康保险', 0)
    if commercial_health > 0:
        max_health = other_standard.get('商业健康保险_最高', 2400)
        amount = min(commercial_health, max_health)
        deductions['商业健康保险'] = amount
        total += amount
    
    # 税收递延养老保险
    pension_insurance = other_config.get('税收递延养老保险', 0)
    if pension_insurance > 0:
        max_pension = other_standard.get('税收递延养老保险_最高', 12000)
        amount = min(pension_insurance, max_pension)
        deductions['税收递延养老保险'] = amount
        total += amount
    
    return total, deductions


def calculate_mainland_salary_tax(annual_income, use_config=True, config=None):
    """
    计算中国大陆个人所得税 (工资、薪金所得)
    
    采用7级超额累进税率
    年度综合所得 = 年收入 - 6万元(起征点) - 专项扣除 - 专项附加扣除 - 依法确定的其他扣除
    
    参数:
        annual_income: 年度工资收入 (人民币)
        use_config: 是否使用配置文件中的扣除项
        config: 自定义配置(如不提供则从配置文件读取)
    
    返回:
        dict: 包含应缴税额、税率等详细信息
    """
    # 计算总扣除额
    total_deductions = 0
    deduction_details = {}
    
    if use_config:
        if config is None:
            all_config = load_config()
            config = all_config.get('我的扣除配置_大陆', {})
        total_deductions, deduction_details = calculate_mainland_deductions(config)
    else:
        # 默认只使用基本减除费用
        total_deductions = 60000
        deduction_details = {'基本减除费用': 60000}
    
    # 7级超额累进税率表
    TAX_BRACKETS = [
        (36000, 0.03, 0),           # 不超过36,000元的部分，税率3%
        (144000, 0.10, 2520),       # 超过36,000元至144,000元的部分，税率10%
        (300000, 0.20, 16920),      # 超过144,000元至300,000元的部分，税率20%
        (420000, 0.25, 31920),      # 超过300,000元至420,000元的部分，税率25%
        (660000, 0.30, 52920),      # 超过420,000元至660,000元的部分，税率30%
        (960000, 0.35, 85920),      # 超过660,000元至960,000元的部分，税率35%
        (float('inf'), 0.45, 181920)  # 超过960,000元的部分，税率45%
    ]
    
    # 计算应纳税所得额 (扣除所有可扣除项)
    taxable_income = max(0, annual_income - total_deductions)
    
    # 计算应纳税额
    tax = 0
    applicable_rate = 0
    quick_deduction = 0
    
    for bracket_limit, rate, deduction in TAX_BRACKETS:
        if taxable_income <= bracket_limit:
            applicable_rate = rate
            quick_deduction = deduction
            tax = taxable_income * rate - deduction
            break
    
    return {
        "年度总收入": annual_income,
        "总扣除额": round(total_deductions, 2),
        "扣除明细": deduction_details,
        "应纳税所得额": taxable_income,
        "适用税率": f"{applicable_rate * 100}%",
        "速算扣除数": quick_deduction,
        "应缴税额": round(max(0, tax), 2),
        "实际税率": round(max(0, tax) / annual_income * 100, 2) if annual_income > 0 else 0,
        "税后收入": round(annual_income - max(0, tax), 2)
    }


def calculate_5year_savings(annual_salary_hkd, years=5, scenarios=None, config=None, 
                           mpf_annual=18000, social_insurance_annual=21312):
    """
    计算5年后在不同生活模式下的剩余金额
    
    参数:
        annual_salary_hkd: 香港年薪(港币)
        years: 计算年数(默认5年)
        scenarios: 要计算的场景列表,默认计算所有场景
                  可选: ['香港工作_香港生活', '香港工作_内地生活']
        config: 自定义配置(如不提供则从配置文件读取)
        mpf_annual: MPF年度供款(港币),默认18000
        social_insurance_annual: 五险一金年度缴纳(人民币),默认21312
    
    返回:
        dict: 各场景的详细计算结果
    """
    if config is None:
        config = load_config()
    
    if scenarios is None:
        scenarios = ['香港工作_香港生活', '香港工作_内地生活']
    
    life_cost_config = config.get('生活成本配置', {})
    
    results = {}
    currency_rate = config.get('港币兑人民币汇率', 0.9)
    for scenario in scenarios:
        if scenario not in life_cost_config:
            print(f"警告: 配置文件中未找到场景 '{scenario}'")
            continue
        
        scenario_config = life_cost_config[scenario]
        currency = scenario_config.get('货币单位', 'HKD')
        
        # 初始化年度支出明细
        annual_breakdown = {
            '收入': {},
            '支出': {},
            '净储蓄': 0
        }
        # 1. 计算年收入和税费
        if scenario == '香港工作_香港生活':
            # 香港工作香港生活
            annual_income = annual_salary_hkd
            
            # 计算香港税费
            hk_tax_config = config.get('我的扣除配置_香港', {})
            tax_result = calculate_hk_salary_tax(annual_salary_hkd, use_config=True, config=hk_tax_config)
            
            annual_breakdown['收入']['年薪'] = annual_income
            annual_breakdown['支出']['香港薪俸税'] = tax_result['应缴税额']
            annual_breakdown['支出']['MPF强制性公积金'] = mpf_annual
            annual_breakdown['支出']['五险一金'] = social_insurance_annual
            # 税后收入 - MPF(换算成人民币) - 五险一金
            after_deductions_income = tax_result['税后收入'] - mpf_annual - social_insurance_annual/currency_rate
            
        elif scenario == '香港工作_内地生活':
            # 香港工作内地生活
            # 重要: 如果在内地居住超过183天,会被认定为中国税务居民
            # 需要就全球收入在中国缴纳个人所得税
            annual_income_cny = annual_salary_hkd * currency_rate
            
            # 使用大陆个税计算(因为是税务居民)
            mainland_tax_config = config.get('我的扣除配置_大陆', {})
            tax_result = calculate_mainland_salary_tax(annual_income_cny, use_config=True, config=mainland_tax_config)
            
            annual_breakdown['收入']['年薪(HKD)'] = annual_salary_hkd
            annual_breakdown['收入']['年薪(CNY)'] = annual_income_cny
            annual_breakdown['收入']['汇率'] = currency_rate
            annual_breakdown['支出']['中国个人所得税'] = tax_result['应缴税额']
            annual_breakdown['支出']['MPF强制性公积金'] = mpf_annual * currency_rate
            annual_breakdown['支出']['五险一金'] = social_insurance_annual
            
            # 税后收入 - MPF(换算成人民币) - 五险一金
            after_deductions_income = tax_result['税后收入'] - (mpf_annual * currency_rate) - social_insurance_annual
        # 2. 计算生活成本支出
        living_costs = 0
        
        # 房租
        rent = scenario_config.get('房租_月', 0) * 12
        annual_breakdown['支出']['房租'] = rent
        living_costs += rent
        
        # 水电煤气费
        utilities = scenario_config.get('水电煤气费_月', 0) * 12
        if utilities > 0:
            annual_breakdown['支出']['水电煤气费'] = utilities
            living_costs += utilities
        
        # 网费
        internet = scenario_config.get('网费_月', 0) * 12
        if internet > 0:
            annual_breakdown['支出']['网费'] = internet
            living_costs += internet
        
        # 交通费
        transport = scenario_config.get('交通费_月', 0) * 12
        annual_breakdown['支出']['交通费'] = transport
        living_costs += transport
        
        # 餐饮
        food = scenario_config.get('餐饮_月', 0) * 12
        annual_breakdown['支出']['餐饮'] = food
        living_costs += food
        
        # 日常用品
        daily = scenario_config.get('日常用品_月', 0) * 12
        annual_breakdown['支出']['日常用品'] = daily
        living_costs += daily
        
        # 医疗保险
        medical = scenario_config.get('医疗保险_年', 0)
        annual_breakdown['支出']['医疗保险'] = medical
        living_costs += medical
        
        # 其他支出
        other = scenario_config.get('其他支出_月', 0) * 12
        annual_breakdown['支出']['其他支出'] = other
        living_costs += other
        
        # 3. 计算年度净储蓄
        annual_savings = after_deductions_income - living_costs
        annual_breakdown['净储蓄'] = annual_savings
        
        # 4. 计算N年累计
        total_savings = annual_savings * years
        
        results[scenario] = {
            '货币单位': currency,
            '年度收支明细': annual_breakdown,
            '年度净储蓄': round(annual_savings, 2),
            f'{years}年累计储蓄': round(total_savings, 2),
            '计算年数': years
        }
    
    return results


def calculate_staged_savings(annual_salary_hkd, stages, config=None,
                            mpf_annual=18000, social_insurance_annual=21312):
    """
    计算分阶段在不同地方生活的储蓄情况
    
    参数:
        annual_salary_hkd: 香港年薪(港币)
        stages: 阶段配置列表,每个阶段包含:
                [
                    {
                        'scenario': '香港工作_内地生活',
                        'years': 3,
                        'custom_costs': {  # 可选: 自定义成本覆盖默认配置
                            '房租_月': 5000,
                            '交通费_月': 1000,
                            # ... 其他成本项
                        }
                    },
                    {'scenario': '香港工作_香港生活', 'years': 2}
                ]
        config: 自定义配置(如不提供则从配置文件读取)
        mpf_annual: MPF年度供款(港币),默认18000
        social_insurance_annual: 五险一金年度缴纳(人民币),默认21312
    
    返回:
        dict: 分阶段储蓄详情和总计
    """
    if config is None:
        config = load_config()
    
    exchange_rate = config.get('港币兑人民币汇率', 0.9)
    
    # 存储每个阶段的结果
    stage_results = []
    total_savings_cny = 0
    total_years = 0
    
    for stage_idx, stage in enumerate(stages, 1):
        scenario = stage['scenario']
        years = stage['years']
        custom_costs = stage.get('custom_costs', {})
        total_years += years
        
        # 如果有自定义成本,创建临时配置
        if custom_costs:
            temp_config = config.copy()
            life_cost_config = temp_config.get('生活成本配置', {}).copy()
            scenario_config = life_cost_config.get(scenario, {}).copy()
            
            # 用自定义成本覆盖默认配置
            scenario_config.update(custom_costs)
            life_cost_config[scenario] = scenario_config
            temp_config['生活成本配置'] = life_cost_config
            
            stage_config = temp_config
        else:
            stage_config = config
        
        # 计算该阶段的储蓄
        result = calculate_5year_savings(
            annual_salary_hkd=annual_salary_hkd,
            years=years,
            scenarios=[scenario],
            config=stage_config,
            mpf_annual=mpf_annual,
            social_insurance_annual=social_insurance_annual
        )
        
        stage_data = result[scenario]
        
        # 统一换算成CNY
        if stage_data['货币单位'] == 'HKD':
            savings_cny = stage_data[f'{years}年累计储蓄'] * exchange_rate
        else:
            savings_cny = stage_data[f'{years}年累计储蓄']
        
        total_savings_cny += savings_cny
        
        stage_info = {
            '阶段': stage_idx,
            '生活场景': scenario,
            '年数': years,
            '货币单位': stage_data['货币单位'],
            '年度净储蓄': stage_data['年度净储蓄'],
            f'{years}年累计储蓄': stage_data[f'{years}年累计储蓄'],
            '累计储蓄(CNY)': round(savings_cny, 2),
            '年度收支明细': stage_data['年度收支明细']
        }
        
        # 如果有自定义成本,记录下来
        if custom_costs:
            stage_info['自定义成本'] = custom_costs
        
        stage_results.append(stage_info)
    
    return {
        '总年数': total_years,
        '总累计储蓄(CNY)': round(total_savings_cny, 2),
        '汇率': exchange_rate,
        '阶段详情': stage_results
    }


def print_staged_savings(result):
    """
    打印分阶段储蓄结果
    
    参数:
        result: calculate_staged_savings函数返回的结果
    """
    print("\n" + "=" * 80)
    print(f"{'分阶段生活储蓄分析':^76}")
    print("=" * 80)
    
    print(f"\n  总年数: {result['总年数']}年")
    print(f"  汇率: 1 HKD = {result['汇率']} CNY")
    print(f"  总累计储蓄: CNY {result['总累计储蓄(CNY)']:,.2f}")
    
    # 打印每个阶段的详情
    for stage in result['阶段详情']:
        print(f"\n{'='*80}")
        stage_title = f"【阶段{stage['阶段']}】{stage['生活场景']} - {stage['年数']}年"
        if '自定义成本' in stage:
            stage_title += " (自定义成本)"
        print(f"  {stage_title}")
        print(f"{'-'*80}")
        
        # 如果有自定义成本,显示出来
        if '自定义成本' in stage:
            print("\n    自定义成本覆盖:")
            for key, value in stage['自定义成本'].items():
                print(f"      {key}: {value}")
        
        # 收入部分
        print("\n    收入:")
        for key, value in stage['年度收支明细']['收入'].items():
            if isinstance(value, (int, float)):
                if key == '汇率':
                    print(f"      {key}: {value}")
                else:
                    print(f"      {key}: {value:,.2f}")
            else:
                print(f"      {key}: {value}")
        
        # 支出部分
        print("\n    支出:")
        total_expense = 0
        for key, value in stage['年度收支明细']['支出'].items():
            print(f"      {key}: {stage['货币单位']} {value:,.2f}")
            total_expense += value
        print(f"      {'总支出':}: {stage['货币单位']} {total_expense:,.2f}")
        
        # 储蓄部分
        print("\n    储蓄:")
        print(f"      年度净储蓄: {stage['货币单位']} {stage['年度净储蓄']:,.2f}")
        print(f"      {stage['年数']}年累计储蓄: {stage['货币单位']} {stage[f'{stage['年数']}年累计储蓄']:,.2f}")
        print(f"      {stage['年数']}年累计储蓄(CNY): CNY {stage['累计储蓄(CNY)']:,.2f}")
    
    print("\n" + "=" * 80)
    print(f"  【总结】{result['总年数']}年总累计储蓄: CNY {result['总累计储蓄(CNY)']:,.2f}")
    print("=" * 80)


def print_savings_comparison(results, exchange_rate=0.9):
    """
    打印5年储蓄对比结果
    
    参数:
        results: calculate_5year_savings函数返回的结果
        exchange_rate: 港币兑人民币汇率
    """
    print("\n" + "=" * 80)
    print(f"{'生活模式储蓄对比分析':^76}")
    print("=" * 80)
    
    for scenario, data in results.items():
        currency = data['货币单位']
        years = data['计算年数']
        
        print(f"\n【{scenario}】")
        print("-" * 80)
        
        # 收入部分
        print("\n  收入:")
        for key, value in data['年度收支明细']['收入'].items():
            if isinstance(value, (int, float)):
                if key == '汇率':
                    print(f"    {key}: {value}")
                else:
                    print(f"    {key}: {value:,.2f}")
            else:
                print(f"    {key}: {value}")
        
        # 支出部分
        print("\n  支出:")
        total_expense = 0
        for key, value in data['年度收支明细']['支出'].items():
            print(f"    {key}: {currency} {value:,.2f}")
            total_expense += value
        print(f"    {'总支出':}: {currency} {total_expense:,.2f}")
        
        # 储蓄部分
        print("\n  储蓄:")
        print(f"    年度净储蓄: {currency} {data['年度净储蓄']:,.2f}")
        print(f"    {years}年累计储蓄: {currency} {data[f'{years}年累计储蓄']:,.2f}")
        
        # 计算储蓄率(基于第一个收入项)
        first_income = list(data['年度收支明细']['收入'].values())[0]
        if isinstance(first_income, (int, float)):
            print(f"    年储蓄率: {(data['年度净储蓄'] / first_income * 100):.2f}%")
    
    # 对比分析
    if len(results) >= 2:
        print("\n" + "=" * 80)
        print(f"{'对比分析':^76}")
        print("=" * 80)
        
        scenarios_list = list(results.keys())
        years = results[scenarios_list[0]]['计算年数']
        
        # 将所有储蓄统一换算为CNY进行对比
        savings_in_cny = {}
        for scenario, data in results.items():
            total_savings = data[f'{years}年累计储蓄']
            currency = data['货币单位']
            
            if currency == 'HKD':
                # 港币转人民币
                savings_in_cny[scenario] = {
                    '原始储蓄': total_savings,
                    '原始货币': currency,
                    'CNY储蓄': total_savings * exchange_rate
                }
            else:
                # 已经是人民币
                savings_in_cny[scenario] = {
                    '原始储蓄': total_savings,
                    '原始货币': currency,
                    'CNY储蓄': total_savings
                }
        
        # 找出最优方案(按CNY比较)
        best_scenario = max(savings_in_cny.keys(), key=lambda x: savings_in_cny[x]['CNY储蓄'])
        best_data = savings_in_cny[best_scenario]
        
        print(f"\n  最优方案: {best_scenario}")
        print(f"  {years}年累计储蓄: {best_data['原始货币']} {best_data['原始储蓄']:,.2f} (CNY {best_data['CNY储蓄']:,.2f})")
        
        # 计算差异
        print(f"\n  汇率: 1 HKD = {exchange_rate} CNY")
        print("\n  详细对比:")
        for scenario in scenarios_list:
            data = savings_in_cny[scenario]
            print(f"    {scenario}:")
            print(f"      {data['原始货币']} {data['原始储蓄']:,.2f} = CNY {data['CNY储蓄']:,.2f}")
            
            if scenario != best_scenario:
                diff_cny = best_data['CNY储蓄'] - data['CNY储蓄']
                percentage = (diff_cny / data['CNY储蓄'] * 100) if data['CNY储蓄'] > 0 else 0
                print(f"      相比最优方案少存: CNY {diff_cny:,.2f} ({percentage:.2f}%)")
    
    print("\n" + "=" * 80)


def compare_tax(annual_income_hkd, exchange_rate=0.92):
    """
    比较相同收入水平在香港和大陆的税负差异
    
    参数:
        annual_income_hkd: 年收入(港币)
        exchange_rate: 汇率 (港币兑人民币)
    
    返回:
        dict: 两地税负对比
    """
    annual_income_cny = annual_income_hkd * exchange_rate
    
    hk_tax = calculate_hk_salary_tax(annual_income_hkd)
    mainland_tax = calculate_mainland_salary_tax(annual_income_cny)
    
    print("\n" + "="*60)
    print("香港与大陆个人所得税对比")
    print("="*60)
    print(f"\n假设年收入: HKD {annual_income_hkd:,.0f} (CNY {annual_income_cny:,.0f})")
    print(f"汇率: 1 HKD = {exchange_rate} CNY")
    
    print("\n【香港薪俸税】")
    for key, value in hk_tax.items():
        if isinstance(value, (int, float)) and key != "实际税率":
            print(f"  {key}: HKD {value:,.2f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n【中国大陆个人所得税】")
    for key, value in mainland_tax.items():
        if isinstance(value, (int, float)) and key != "实际税率":
            print(f"  {key}: CNY {value:,.2f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n【对比分析】")
    hk_tax_cny = hk_tax["应缴税额"] * exchange_rate
    mainland_tax_amount = mainland_tax["应缴税额"]
    difference = mainland_tax_amount - hk_tax_cny
    
    print(f"  香港应缴税额(换算): CNY {hk_tax_cny:,.2f}")
    print(f"  大陆应缴税额: CNY {mainland_tax_amount:,.2f}")
    print(f"  税负差异: CNY {abs(difference):,.2f} ({'大陆多交' if difference > 0 else '香港多交'})")
    print(f"  香港实际税率: {hk_tax['实际税率']}%")
    print(f"  大陆实际税率: {mainland_tax['实际税率']}%")
    print("="*60)
    
    return {
        "香港": hk_tax,
        "大陆": mainland_tax,
        "税负差异(CNY)": round(difference, 2)
    }


# 示例使用
if __name__ == "__main__":
    print("=" * 60)
    print("香港与大陆个人所得税计算器(支持自定义扣除项)")
    print("=" * 60)
    income_hkd = 650000
    # 加载配置
    config = load_config()
    
    # 示例1: 使用默认配置计算香港薪俸税
    print("\n【示例1】香港年收入 HKD 652,827 (使用默认配置)")
    hk_result = calculate_hk_salary_tax(income_hkd, use_config=True)
    for key, value in hk_result.items():
        if key == "扣除明细":
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    - {k}: HKD {v:,.2f}")
        elif isinstance(value, (int, float)) and key not in ["实际税率"]:
            print(f"  {key}: HKD {value:,.2f}")
        else:
            print(f"  {key}: {value}")
    
    # 示例2: 使用默认配置计算大陆个人所得税
    print("\n【示例2】大陆年收入 CNY 587,544 (使用默认配置)")
    mainland_result = calculate_mainland_salary_tax(income_hkd*0.9, use_config=True)
    for key, value in mainland_result.items():
        if key == "扣除明细":
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    - {k}: CNY {v:,.2f}")
        elif isinstance(value, (int, float)) and key not in ["实际税率"]:
            print(f"  {key}: CNY {value:,.2f}")
        else:
            print(f"  {key}: {value}")
    
    # 示例3: 计算5年后不同生活模式下的储蓄对比
    print("\n" + "=" * 60)
    print("【示例3】5年储蓄对比分析")
    print("=" * 60)
    print("\n假设: 香港年薪 HKD 652,827")
    print("场景对比: 香港工作香港生活 vs 香港工作内地生活")
    
    # 从配置文件读取汇率
    exchange_rate = config.get('港币兑人民币汇率', 0.9)
    
    savings_results = calculate_5year_savings(
        annual_salary_hkd=income_hkd,
        years=5,
        scenarios=['香港工作_香港生活', '香港工作_内地生活']
    )
    
    print_savings_comparison(savings_results, exchange_rate=exchange_rate)
    
    
    # 配置分阶段方案 - 带自定义成本(1)
    # 示例4: 分阶段生活储蓄计算
    print("\n" + "=" * 60)
    print("【示例4】分阶段生活储蓄分析")
    print("=" * 60)
    print("\n假设: 香港年薪 HKD 650,000")
    print("方案: 前3年在内地生活(房租7000),后2年在香港生活(幼儿园，房租20000)")
    stages = [
        {
            'scenario': '香港工作_内地生活',
            'years': 3
        },
        {
            'scenario': '香港工作_香港生活',
            'years': 2,
            'custom_costs': {
                '房租_月': 20000,
            }
        }
    ]
    
    staged_result = calculate_staged_savings(
        annual_salary_hkd=income_hkd,
        stages=stages
    )
    
    print_staged_savings(staged_result)

    # 配置分阶段方案 - 带自定义成本(2)
    stages = [
        {
            'scenario': '香港工作_香港生活',
            'years': 3,
            'custom_costs': {
                '房租_月': 16500,
            }
        },
        {
            'scenario': '香港工作_香港生活',
            'years': 2,
            'custom_costs': {
                '房租_月': 20000, 
            }
        }
    ]
    
    staged_result = calculate_staged_savings(
        annual_salary_hkd=income_hkd,
        stages=stages
    )
    
    print_staged_savings(staged_result)


