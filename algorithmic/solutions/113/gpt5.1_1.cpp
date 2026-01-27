#include <bits/stdc++.h>
using namespace std;

struct Node {
    unsigned long long state;
    int parent;
    unsigned char src, dst; // 0,1,2 for baskets; 255 for root
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    // Powers of 3 for encoding
    static unsigned long long pow3[31];
    pow3[0] = 1;
    for (int i = 1; i <= N; ++i) pow3[i] = pow3[i - 1] * 3ull;

    // Initial state: all balls in basket 1 -> digit 0
    unsigned long long startState = 0;
    // Goal state: all balls in basket 3 -> digit 2
    unsigned long long goalState = 0;
    for (int i = 0; i < N; ++i) goalState += 2ull * pow3[i];

    if (startState == goalState) {
        cout << 0 << '\n';
        return 0;
    }

    // BFS structures
    vector<Node> nodes;
    nodes.reserve(2000000);
    unordered_map<unsigned long long, int> vis;
    vis.reserve(2000000);

    nodes.push_back({startState, -1, 255, 255});
    vis[startState] = 0;

    vector<int> queueIdx;
    queueIdx.reserve(2000000);
    queueIdx.push_back(0);

    int goalIdx = -1;

    // Temporary buffers reused per node
    vector<unsigned char> pos(N + 1);      // 1-based ball -> basket (0,1,2)
    vector<int> bucket[3];                 // balls in each basket

    for (size_t qi = 0; qi < queueIdx.size(); ++qi) {
        int idx = queueIdx[qi];
        unsigned long long s = nodes[idx].state;

        if (s == goalState) {
            goalIdx = idx;
            break;
        }

        // Decode state into pos and buckets
        unsigned long long tmp = s;
        bucket[0].clear();
        bucket[1].clear();
        bucket[2].clear();
        for (int i = 1; i <= N; ++i) {
            unsigned char b = tmp % 3ull;
            tmp /= 3ull;
            pos[i] = b;
            bucket[b].push_back(i); // ascending order since i increases
        }

        // Compute center ball for each basket
        int center[3];
        for (int b = 0; b < 3; ++b) {
            if (!bucket[b].empty()) {
                int k = (int)bucket[b].size();
                int idxCenter = k / 2; // floor(k/2), 0-based
                center[b] = bucket[b][idxCenter];
            } else {
                center[b] = -1;
            }
        }

        // Generate moves
        for (int src = 0; src < 3; ++src) {
            if (center[src] == -1) continue;
            int x = center[src];
            int xIdx = x - 1;

            for (int dst = 0; dst < 3; ++dst) {
                if (dst == src) continue;

                const auto &destVec = bucket[dst];
                int t = (int)destVec.size();

                // Count how many in dest are < x
                int less = 0;
                for (int v : destVec) {
                    if (v < x) ++less;
                    else break; // since destVec is sorted ascending
                }

                if (less == (t + 1) / 2) {
                    // Move is valid
                    unsigned long long newState;
                    if (dst > src)
                        newState = s + (unsigned long long)(dst - src) * pow3[xIdx];
                    else
                        newState = s - (unsigned long long)(src - dst) * pow3[xIdx];

                    auto it = vis.find(newState);
                    if (it == vis.end()) {
                        int newIdx = (int)nodes.size();
                        nodes.push_back({newState, idx, (unsigned char)src, (unsigned char)dst});
                        vis.emplace(newState, newIdx);
                        queueIdx.push_back(newIdx);

                        if (newState == goalState) {
                            goalIdx = newIdx;
                            qi = queueIdx.size(); // break outer loop
                            break;
                        }
                    }
                }
            }
        }
    }

    // Reconstruct path
    vector<pair<int,int>> moves;
    int cur = goalIdx;
    while (cur != -1 && nodes[cur].parent != -1) {
        Node &nd = nodes[cur];
        moves.push_back({(int)nd.src + 1, (int)nd.dst + 1});
        cur = nd.parent;
    }
    reverse(moves.begin(), moves.end());

    cout << moves.size() << '\n';
    for (auto &mv : moves) {
        cout << mv.first << ' ' << mv.second << '\n';
    }

    return 0;
}