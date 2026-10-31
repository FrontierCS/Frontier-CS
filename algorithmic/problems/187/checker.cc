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
#include <map>

using namespace std;

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // 1. 读取输入数据
    int n = inf.readInt();
    int m = inf.readInt();

    // 使用 set 存储边，方便 O(log M) 查询
    // 将 (u, v) 编码为 long long: u * 1000000 + v (确保 u < v)
    // 假设 N < 1,000,000
    set<long long> edge_set;
    const long long BASE = 1000000LL;

    for (int i = 0; i < m; ++i) {
        int u = inf.readInt();
        int v = inf.readInt();
        if (u > v) swap(u, v);
        edge_set.insert(u * BASE + v);
    }

    // 2. 读取用户输出
    // map: clique_id -> list of nodes
    map<int, vector<int>> cliques;
    for (int i = 1; i <= n; ++i) {
        int cid = ouf.readInt();
        cliques[cid].push_back(i);
    }

    // 3. 验证合法性
    // 对于每个团，检查其中所有节点对是否存在边
    for (auto const& [cid, nodes] : cliques) {
        int size = nodes.size();
        if (size <= 1) continue; // 单个点显然是一个团

        for (int i = 0; i < size; ++i) {
            for (int j = i + 1; j < size; ++j) {
                int u = nodes[i];
                int v = nodes[j];
                if (u > v) swap(u, v);
                
                // 检查边 (u, v) 是否存在
                if (edge_set.find(u * BASE + v) == edge_set.end()) {
                    quitf(_wa, "Invalid clique cover: Node %d and Node %d are in the same group (ID %d) but contain no edge.", nodes[i], nodes[j], cid);
                }
            }
        }
    }

    // 4. 输出结果
    int k = cliques.size();

    //Optimal Solution:
    int K_reference = ans.readInt();

    if (K_reference <= 0) quitf(_fail, "Reference count must be positive.");
    const double r = (double)K_reference / k;
    const double old_ratio = r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
    const double ratio = natural_log_score(100.0L*old_ratio, k, K_reference, true)/100.0;
    quitf(_ok, "Valid clique cover. Used %d cliques, Reference: %d, Performance: %.12f, Ratio: %.12f, RatioUnbounded: %.12f",
          k, K_reference, r, ratio, ratio);
}
