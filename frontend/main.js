const apiBase = ""; // 同源部署时可留空

async function fetchJSON(url, options = {}) {
  const res = await fetch(apiBase + url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json();
}

// ========== 模块一：分阶段生活配置与储蓄计算 ==========

function initStagedModule() {
  const stagesTextarea = document.getElementById("stages-json");
  const salaryInput = document.getElementById("stage-salary");
  const btn = document.getElementById("btn-calc-staged");
  const resultDiv = document.getElementById("staged-result");

  // 初始化一个示例配置
  const defaultStages = [
    {
      scenario: "香港工作_内地生活",
      years: 2,
      custom_costs: {
        房租_月: 7500,
      },
    },
    {
      scenario: "香港工作_香港生活",
      years: 3,
      custom_costs: {
        房租_月: 17000,
      },
    },
  ];
  stagesTextarea.value = JSON.stringify(defaultStages, null, 2);

  btn.addEventListener("click", async () => {
    try {
      const salary = Number(salaryInput.value || 0);
      const stages = JSON.parse(stagesTextarea.value || "[]");
      const payload = { annual_salary_hkd: salary, stages };
      const data = await fetchJSON("/api/staged-savings", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      renderStagedResult(resultDiv, data);
    } catch (e) {
      resultDiv.innerHTML = `<div class="error">${e.message}</div>`;
    }
  });
}

function renderStagedResult(container, data) {
  const lines = [];
  lines.push(`<p><strong>总年数</strong>: ${data.总年数} 年</p>`);
  const totalCny = data["总累计储蓄(CNY)"];
  lines.push(`<p><strong>总累计储蓄</strong>: CNY ${totalCny != null ? totalCny : "-"}</p>`);

  lines.push("<hr />");

  (data.阶段详情 || []).forEach((stage) => {
    lines.push(`<div class="stage-block">`);
    lines.push(
      `<h4>阶段 ${stage.阶段} - ${stage.生活场景} (${stage.年数} 年)</h4>`
    );
    if (stage.自定义成本) {
      lines.push("<p><strong>自定义成本覆盖:</strong></p><ul>");
      Object.entries(stage.自定义成本).forEach(([k, v]) => {
        lines.push(`<li>${k}: ${v}</li>`);
      });
      lines.push("</ul>");
    }
    const annualNet = stage.年度净储蓄;
    const annualNetStr =
      annualNet != null ? annualNet.toLocaleString() : "-";
    lines.push(
      `<p><strong>年度净储蓄</strong>: ${stage.货币单位} ${annualNetStr}</p>`
    );
    const key = `${stage.年数}年累计储蓄`;
    const stageTotal = stage[key];
    const stageTotalStr =
      stageTotal != null ? stageTotal.toLocaleString() : "-";
    lines.push(
      `<p><strong>${key}</strong>: ${stage.货币单位} ${stageTotalStr}</p>`
    );
    const stageCny = stage["累计储蓄(CNY)"];
    const stageCnyStr =
      stageCny != null ? stageCny.toLocaleString() : "-";
    lines.push(
      `<p><strong>${stage.年数}年累计储蓄(CNY)</strong>: CNY ${stageCnyStr}</p>`
    );
    lines.push("</div>");
  });

  container.innerHTML = lines.join("\n");
}

// ========== 模块二：敏感性分析 ==========

let sensChart;

function initSensitivityModule() {
  const salaryInput = document.getElementById("sens-salary");
  const yearsInput = document.getElementById("sens-years");
  const scenarioSelect = document.getElementById("sens-scenario");
  const itemSelect = document.getElementById("sens-item");
  const startInput = document.getElementById("sens-start");
  const endInput = document.getElementById("sens-end");
  const stepInput = document.getElementById("sens-step");
  const btn = document.getElementById("btn-sens-run");
  const summaryDiv = document.getElementById("sens-summary");
  const ctx = document.getElementById("sens-chart").getContext("2d");

  btn.addEventListener("click", async () => {
    try {
      const payload = {
        annual_salary_hkd: Number(salaryInput.value || 0),
        years: Number(yearsInput.value || 5),
        scenario: scenarioSelect.value,
        varied_item: itemSelect.value,
        start: Number(startInput.value || 0),
        end: Number(endInput.value || 0),
        step: Number(stepInput.value || 1000),
      };
      const data = await fetchJSON("/api/sensitivity", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      const labels = data.values;
      const values = data.savings_cny;

      if (sensChart) sensChart.destroy();
      sensChart = new Chart(ctx, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "总累计储蓄 (CNY)",
              data: values,
              borderColor: "#007bff",
              tension: 0.2,
              fill: false,
            },
          ],
        },
        options: {
          responsive: true,
          scales: {
            x: {
              title: { display: true, text: `${data.varied_item} 金额 (月)` },
            },
            y: {
              title: { display: true, text: "总累计储蓄 (CNY)" },
            },
          },
        },
      });

      const min = Math.min(...values);
      const max = Math.max(...values);
      const idxBest = values.indexOf(max);
      const bestCost = labels[idxBest];

      summaryDiv.innerHTML = `
        <p><strong>分析场景</strong>: ${data.scenario}</p>
        <p><strong>年薪</strong>: HKD ${data.annual_salary_hkd.toLocaleString()}, 年数: ${data.years}</p>
        <p><strong>最优 ${data.varied_item}</strong>: 月 ${bestCost}, 对应累计储蓄约 CNY ${max.toLocaleString()}</p>
        <p><strong>区间储蓄范围</strong>: CNY ${min.toLocaleString()} ~ ${max.toLocaleString()}</p>
      `;
    } catch (e) {
      summaryDiv.innerHTML = `<div class="error">${e.message}</div>`;
    }
  });
}

// ========== 模块三:两地生活对比与交叉点 ==========

let crossChart;

function initCrossModule() {
  const salaryInput = document.getElementById("cross-salary");
  const yearsInput = document.getElementById("cross-years");
  const hkItemSelect = document.getElementById("cross-hk-item");
  const hkStartInput = document.getElementById("cross-hk-start");
  const hkEndInput = document.getElementById("cross-hk-end");
  const hkStepInput = document.getElementById("cross-hk-step");
  const cnItemSelect = document.getElementById("cross-cn-item");
  const cnStartInput = document.getElementById("cross-cn-start");
  const cnEndInput = document.getElementById("cross-cn-end");
  const cnStepInput = document.getElementById("cross-cn-step");
  const btn = document.getElementById("btn-cross-run");
  const summaryDiv = document.getElementById("cross-summary");
  const ctx = document.getElementById("cross-chart").getContext("2d");

  btn.addEventListener("click", async () => {
    try {
      const payload = {
        annual_salary_hkd: Number(salaryInput.value || 0),
        years: Number(yearsInput.value || 5),
        hk_varied_item: hkItemSelect.value,
        hk_start: Number(hkStartInput.value || 0),
        hk_end: Number(hkEndInput.value || 0),
        hk_step: Number(hkStepInput.value || 1000),
        cn_varied_item: cnItemSelect.value,
        cn_start: Number(cnStartInput.value || 0),
        cn_end: Number(cnEndInput.value || 0),
        cn_step: Number(cnStepInput.value || 1000),
      };
      const data = await fetchJSON("/api/lifestyle-cross-over", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      // 横轴: 累计储蓄(CNY)
      // 两条线: 香港消费项金额 vs 内地消费项金额
      const hkData = data.hk_savings.map((saving, i) => ({
        x: saving,
        y: data.hk_costs[i],
      }));
      const cnData = data.cn_savings.map((saving, i) => ({
        x: saving,
        y: data.cn_costs[i],
      }));

      if (crossChart) crossChart.destroy();

      // 自定义插件:实现双向悬停和垂直线
      const crosshairPlugin = {
        id: 'crosshair',
        afterDraw: (chart) => {
          // 安全检查: 确保tooltip存在且有活动点
          if (chart.tooltip && chart.tooltip._active && chart.tooltip._active.length) {
            const ctx = chart.ctx;
            const activePoint = chart.tooltip._active[0];
            const x = activePoint.element.x;
            const topY = chart.scales.y.top;
            const bottomY = chart.scales.y.bottom;

            // 绘制垂直虚线
            ctx.save();
            ctx.beginPath();
            ctx.moveTo(x, topY);
            ctx.lineTo(x, bottomY);
            ctx.lineWidth = 2;
            ctx.strokeStyle = 'rgba(128, 128, 128, 0.5)';
            ctx.setLineDash([5, 5]);
            ctx.stroke();
            ctx.restore();
          }
        }
      };

      crossChart = new Chart(ctx, {
        type: "scatter",
        data: {
          datasets: [
            {
              label: `香港 ${data.hk_varied_item}`,
              data: hkData,
              borderColor: "#007bff",
              backgroundColor: "rgba(0, 123, 255, 0.5)",
              showLine: true,
              tension: 0.2,
              pointRadius: 4,
              pointHoverRadius: 8,
              pointHoverBackgroundColor: "#007bff",
            },
            {
              label: `内地 ${data.cn_varied_item}`,
              data: cnData,
              borderColor: "#28a745",
              backgroundColor: "rgba(40, 167, 69, 0.5)",
              showLine: true,
              tension: 0.2,
              pointRadius: 4,
              pointHoverRadius: 8,
              pointHoverBackgroundColor: "#28a745",
            },
          ],
        },
        options: {
          responsive: true,
          interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false,
          },
          plugins: {
            legend: { position: "top" },
            tooltip: {
              enabled: true,
              mode: 'index',
              intersect: false,
              callbacks: {
                title: function(tooltipItems) {
                  const xValue = tooltipItems[0].parsed.x;
                  return `目标储蓄: CNY ${xValue.toLocaleString()}`;
                },
                label: function (context) {
                  const label = context.dataset.label || '';
                  const cost = context.parsed.y;
                  return `${label}: 月 ${cost.toLocaleString()}`;
                },
                afterLabel: function(context) {
                  // 计算另一条线在相同X轴位置的Y值
                  const currentX = context.parsed.x;
                  const datasetIndex = context.datasetIndex;
                  const otherDatasetIndex = datasetIndex === 0 ? 1 : 0;
                  const otherDataset = context.chart.data.datasets[otherDatasetIndex];
                  
                  // 线性插值找到对应Y值
                  const otherData = otherDataset.data;
                  let otherY = null;
                  
                  for (let i = 0; i < otherData.length - 1; i++) {
                    const x1 = otherData[i].x;
                    const x2 = otherData[i + 1].x;
                    const y1 = otherData[i].y;
                    const y2 = otherData[i + 1].y;
                    
                    if ((x1 <= currentX && currentX <= x2) || (x2 <= currentX && currentX <= x1)) {
                      if (x2 !== x1) {
                        const ratio = (currentX - x1) / (x2 - x1);
                        otherY = y1 + (y2 - y1) * ratio;
                      } else {
                        otherY = y1;
                      }
                      break;
                    }
                  }
                  
                  if (otherY !== null) {
                    const diff = Math.abs(context.parsed.y - otherY);
                    const diffPercent = ((diff / Math.min(context.parsed.y, otherY)) * 100).toFixed(1);
                    return `\n对比 ${otherDataset.label}: 月 ${otherY.toLocaleString()}\n差额: ${diff.toLocaleString()} (${diffPercent}%)`;
                  }
                  return '';
                },
              },
            },
          },
          scales: {
            x: {
              type: "linear",
              title: { display: true, text: "总累计储蓄 (CNY)" },
              ticks: {
                callback: function(value) {
                  return value.toLocaleString();
                }
              }
            },
            y: {
              title: { display: true, text: "消费项金额 (月)" },
              ticks: {
                callback: function(value) {
                  return value.toLocaleString();
                }
              }
            },
          },
        },
        plugins: [crosshairPlugin],
      });

      let summaryHtml = `
        <p><strong>年薪</strong>: HKD ${data.annual_salary_hkd.toLocaleString()}, 年数: ${data.years}</p>
        <p><strong>香港场景</strong>: ${data.hk_varied_item}</p>
        <p><strong>内地场景</strong>: ${data.cn_varied_item}</p>
      `;

      if (data.cross_point) {
        summaryHtml += `
          <p><strong>交叉点</strong>: 在目标储蓄 CNY ${data.cross_point.saving_cny.toLocaleString()} 时:</p>
          <ul>
            <li>香港 ${data.hk_varied_item}: 月 ${data.cross_point.hk_cost.toLocaleString()}</li>
            <li>内地 ${data.cn_varied_item}: 月 ${data.cross_point.cn_cost.toLocaleString()}</li>
          </ul>
          <p>这意味着:如果想要积累 CNY ${data.cross_point.saving_cny.toLocaleString()} 的储蓄,在香港的 ${data.hk_varied_item} 为 ${data.cross_point.hk_cost.toLocaleString()} 和在内地的 ${data.cn_varied_item} 为 ${data.cross_point.cn_cost.toLocaleString()} 时,两种生活方式效果相当。</p>
        `;
      } else if (data.dominant) {
        summaryHtml += `<p><strong>结论</strong>: ${data.dominant}</p>`;
      }

      summaryHtml += `
        <hr style="margin: 1rem 0;" />
        <p style="color: #666; font-size: 0.85rem;">
          <strong>💡 交互提示</strong>: 将鼠标悬停在图表任意数据点上,可查看该储蓄目标下两地消费对比详情。
        </p>
      `;

      summaryDiv.innerHTML = summaryHtml;
    } catch (e) {
      summaryDiv.innerHTML = `<div class="error">${e.message}</div>`;
    }
  });
}

// ========== 页面初始化 ==========

document.addEventListener("DOMContentLoaded", () => {
  initStagedModule();
  initSensitivityModule();
  initCrossModule();
});
