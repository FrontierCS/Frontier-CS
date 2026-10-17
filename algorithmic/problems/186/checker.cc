#include <cmath>
#include <algorithm>

// Keep historical scores through 60; above the anchor, compare physical objectives.
static double natural_log_score(long double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0L) return (double)std::max(0.0L, old_points);
    if (!(value > 0.0L) || !(anchor > 0.0L))
        return (double)std::clamp(old_points, 0.0L, 100.0L);
    const long double improvement = minimize
        ? std::log(anchor) - std::log(value)
        : std::log(value) - std::log(anchor);
    return (double)std::clamp(60.0L + improvement, 0.0L, 100.0L);
}

#include "testlib.h"
#include <vector>
#include <cmath>
#include <set>
#include <algorithm>

using namespace std;

int main(int argc, char* argv[]) {
    // 初始化 testlib
    registerTestlibCmd(argc, argv);

    // 1. 读取输入数据 (Input)
    // -------------------------
    int n = inf.readInt(); // 节点数
    int m = inf.readInt(); // 边数
    
    // 存储边表
    vector<pair<int, int>> edges;
    for (int i = 0; i < m; ++i) {
        int u = inf.readInt();
        int v = inf.readInt();
        edges.push_back({u, v});
    }

    // 2. 读取用户输出 (Output)
    // -------------------------
    // 读取 n 个整数，表示每个点的颜色
    vector<int> colors(n + 1);
    set<int> distinct_colors;
    
    for (int i = 1; i <= n; ++i) {
        colors[i] = ouf.readInt();
        distinct_colors.insert(colors[i]);
    }

    // 3. 验证合法性 (Validation)
    // -------------------------
    for (auto& e : edges) {
        int u = e.first;
        int v = e.second;
        
        // 如果有边相连的两个点颜色相同，判为 Wrong Answer
        if (colors[u] == colors[v]) {
            quitf(_wa, "Invalid coloring: Node %d and Node %d are connected but share color %d.", u, v, colors[u]);
        }
    }

    // 4. 输出结果 (Result)
    // -------------------------
    int k = distinct_colors.size();

    //Optimal Solution:
    int K_reference = ans.readInt();
    
    // 如果你有标准答案文件 (.ans)，可以在这里读取并对比 k 值
    // 这里我们只作为评估工具，返回 OK 并打印使用的颜色数量
    if (K_reference <= 0) quitf(_fail, "Reference count must be positive.");
    const double r = (double)K_reference / k;
    const double old_ratio = r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
    const double ratio = natural_log_score(100.0L*old_ratio, k, K_reference, true)/100.0;
    quitf(_ok, "Valid coloring. Used %d colors, Reference: %d, Performance: %.12f, Ratio: %.12f, RatioUnbounded: %.12f",
          k, K_reference, r, ratio, ratio);
}
