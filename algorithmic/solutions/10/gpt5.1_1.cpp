#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int u, v;
    long long w;
};

long long ask(int u, int v) {
    if (u == v) return 0;
    cout << "? " << u << " " << v << '\n';
    cout.flush();
    long long d;
    if (!(cin >> d)) {
        // In interactive environment, this should not happen.
        exit(0);
    }
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;

        vector<Edge> edges;
        edges.reserve(max(0, n - 1));

        if (n > 0) {
            vector<vector<int>> stack;
            vector<int> initial(n);
            iota(initial.begin(), initial.end(), 1);
            stack.push_back(std::move(initial));

            while (!stack.empty()) {
                vector<int> S = std::move(stack.back());
                stack.pop_back();
                int m = (int)S.size();
                if (m <= 1) continue;

                int A = S[0];

                vector<long long> distA(m), distB(m);
                long long D = 0;
                int idxB = 0;

                // First sweep: from A to find B and get distA.
                for (int i = 0; i < m; ++i) {
                    int v = S[i];
                    if (v == A) {
                        distA[i] = 0;
                    } else {
                        distA[i] = ask(A, v);
                    }
                    if (distA[i] > D) {
                        D = distA[i];
                        idxB = i;
                    }
                }
                int B = S[idxB];

                // Second sweep: from B to get distB.
                for (int i = 0; i < m; ++i) {
                    int v = S[i];
                    if (v == B) {
                        distB[i] = 0;
                    } else {
                        distB[i] = ask(B, v);
                    }
                }

                // Collect nodes on path A-B.
                vector<pair<long long, int>> pathNodes;
                pathNodes.reserve(m);
                for (int i = 0; i < m; ++i) {
                    if (distA[i] + distB[i] == D) {
                        pathNodes.emplace_back(distA[i], S[i]);
                    }
                }

                sort(pathNodes.begin(), pathNodes.end(),
                     [](const pair<long long,int> &x, const pair<long long,int> &y) {
                         return x.first < y.first;
                     });

                // Add edges along the path.
                for (int i = 1; i < (int)pathNodes.size(); ++i) {
                    int u = pathNodes[i - 1].second;
                    int v = pathNodes[i].second;
                    long long w = pathNodes[i].first - pathNodes[i - 1].first;
                    edges.push_back({u, v, w});
                }

                // Map distA on path to vertex.
                unordered_map<long long, int> rootByDist;
                rootByDist.reserve(pathNodes.size() * 2 + 1);
                for (auto &p : pathNodes) {
                    rootByDist[p.first] = p.second;
                }

                // Group vertices by projection root on A-B path.
                unordered_map<int, vector<int>> groups;
                groups.reserve(pathNodes.size() * 2 + 1);
                for (int i = 0; i < m; ++i) {
                    long long num = distA[i] + D - distB[i];
                    long long t = num / 2; // guaranteed integer in tree metric

                    int root;
                    auto it = rootByDist.find(t);
                    if (it != rootByDist.end()) {
                        root = it->second;
                    } else {
                        // Fallback (should not happen in correct tree metric)
                        auto it2 = lower_bound(
                            pathNodes.begin(), pathNodes.end(),
                            pair<long long,int>(t, -1),
                            [](const pair<long long,int>& a,
                               const pair<long long,int>& b) {
                                return a.first < b.first;
                            });
                        if (it2 != pathNodes.end() && it2->first == t) {
                            root = it2->second;
                        } else {
                            // As a very last resort, attach to nearest in terms of distA on path.
                            if (it2 == pathNodes.end()) --it2;
                            root = it2->second;
                        }
                    }
                    groups[root].push_back(S[i]);
                }

                // Recurse on each group (component).
                for (auto &kv : groups) {
                    auto &comp = kv.second;
                    if (comp.size() <= 1) continue;
                    stack.push_back(std::move(comp));
                }
            }
        }

        cout << "!";
        for (const auto &e : edges) {
            cout << " " << e.u << " " << e.v << " " << e.w;
        }
        cout << '\n';
        cout.flush();
    }

    return 0;
}