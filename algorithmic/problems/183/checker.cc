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

#include <cmath>
#include <algorithm>

// Historical calibration supplies the unchanged low-score branch.
static double calibrated(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

#include "testlib.h"
#include <vector>

using namespace std;

int main(int argc, char* argv[]) {
    // 初始化 testlib
    registerTestlibCmd(argc, argv);

    // 1. 读取输入数据 (Input)
    int N = inf.readInt();
    int M = inf.readInt();

    // 存储边列表，用于验证独立性约束
    vector<pair<int, int>> edges;
    edges.reserve(M);
    for (int i = 0; i < M; i++) {
        int u = inf.readInt();
        int v = inf.readInt();
        edges.push_back({u, v});
    }

    // 2. 读取标准答案 (Answer)
    // ans 文件中只包含一个整数 K* (最优/参考解的大小)
    int K_optimal = ans.readInt();

    // 3. 读取选手输出 (Output) 并统计 K
    vector<int> user_sol(N + 1); // 1-based indexing
    int K_user = 0;

    for (int i = 1; i <= N; i++) {
        // 读取 0 或 1
        int val = ouf.readInt(0, 1, format("x_%d", i)); 
        user_sol[i] = val;
        if (val == 1) {
            K_user++;
        }
    }

    // 4. 验证选手的解是否有效 (Validity Check)
    // 独立集定义：选出的点集中，任意两点之间不能有边
    // 也就是说，对于图中任意一条边 (u, v)，不能同时有 user_sol[u] == 1 和 user_sol[v] == 1
    for (int i = 0; i < M; i++) {
        int u = edges[i].first;
        int v = edges[i].second;

        // 如果一条边的两个端点都被选中了，这就不是独立集
        if (user_sol[u] == 1 && user_sol[v] == 1) {
            quitf(_wa, "Invalid Independent Set: Edge %d-%d has both endpoints selected.", u, v);
        }
    }

    if(K_optimal<0 || K_optimal>N) quitf(_fail,"Invalid reference size");
    double performance;
    // Optimize independent-set size directly, not its complement.
    if(K_optimal==0) quitf(_fail,"Independent-set reference must be positive");
    performance=(double)K_user/K_optimal;
    double score=calibrated(performance);
    score = natural_log_score(100.0L * (score), K_user, K_optimal, false) / 100.0;
    quitp(score,"K_user=%d K_reference=%d Ratio: %.12f RatioUnbounded: %.12f",K_user,K_optimal,score,score);
}
