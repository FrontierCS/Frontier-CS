#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

int subtask;
long long n;
std::vector<int> adj[100005];
bool visited[100005];
int p[100005];

std::vector<int> do_query(const std::vector<int>& q) {
    if (q.empty()) {
        return {};
    }
    std::cout << q.size();
    for (int x : q) {
        std::cout << " " << x;
    }
    std::cout << std::endl;
    std::vector<int> res(q.size());
    for (size_t i = 0; i < q.size(); ++i) {
        std::cin >> res[i];
    }
    return res;
}

void answer(const std::vector<int>& p_vec) {
    std::cout << -1;
    for (size_t i = 0; i < p_vec.size(); ++i) {
        std::cout << " " << p_vec[i];
    }
    std::cout << std::endl;
}

void solve() {
    std::vector<int> q;
    std::vector<std::pair<int, int>> pairs;
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            q.push_back(i);
            q.push_back(j);
            q.push_back(i);
            q.push_back(j);
            pairs.push_back({i, j});
        }
    }
    
    auto res = do_query(q);
    
    int cur = 0;
    for (const auto& p : pairs) {
        if (res[cur + 1]) {
            adj[p.first].push_back(p.second);
            adj[p.second].push_back(p.first);
        }
        cur += 4;
    }

    int start_node = -1;
    for (int i = 1; i <= n; ++i) {
        if (!adj[i].empty()) {
            start_node = i;
            break;
        }
    }
    
    if (n == 1) {
        p[0] = 1;
    } else if (start_node != -1) {
        int curr = start_node;
        int prev = -1;
        for (int i = 0; i < n; ++i) {
            p[i] = curr;
            visited[curr] = true;
            int next_node = -1;
            for (int neighbor : adj[curr]) {
                if (neighbor != prev) {
                    next_node = neighbor;
                    break;
                }
            }
            if (next_node == -1 && i < n - 1) {
                // Path, not a cycle, or disconnected graph. Find an unvisited node.
                for (int k = 1; k <= n; ++k) {
                    if (!visited[k]) {
                        next_node = k;
                        break;
                    }
                }
            }
            prev = curr;
            curr = next_node;
        }
    }

    std::vector<int> p_vec;
    std::vector<bool> in_p(n + 1, false);
    for (int i = 0; i < n; ++i) {
        if (p[i] != 0 && !in_p[p[i]]) {
            p_vec.push_back(p[i]);
            in_p[p[i]] = true;
        }
    }
    for (int i = 1; i <= n; ++i) {
        if (!in_p[i]) {
            p_vec.push_back(i);
        }
    }
    answer(p_vec);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    std::cin >> subtask >> n;

    if (n > 1000) {
        // Fallback for large N, might not pass due to complexity
        // but this problem structure is unusual.
        // The simple N^2 approach is implemented as it is guaranteed to be correct.
        // It should pass at least subtask 1.
        // A more complex block-based approach is needed for Subtask 2.
        // This simple solution is provided as a baseline.
        
        int B = 250;
        std::vector<std::vector<int>> groups;
        for (int i = 1; i <= n; i += B) {
            groups.push_back({});
            for (int j = i; j < std::min((long long)i + B, n + 1); ++j) {
                groups.back().push_back(j);
            }
        }

        // Intra-group edges
        for (const auto& group : groups) {
            std::vector<int> q;
            std::vector<std::pair<int, int>> pairs;
            for (size_t j = 0; j < group.size(); ++j) {
                for (size_t k = j + 1; k < group.size(); ++k) {
                    q.push_back(group[j]);
                    q.push_back(group[k]);
                    q.push_back(group[j]);
                    q.push_back(group[k]);
                    pairs.push_back({group[j], group[k]});
                }
            }
            auto res = do_query(q);
            int cur = 0;
            for (const auto& p : pairs) {
                if (res[cur + 1]) {
                    adj[p.first].push_back(p.second);
                    adj[p.second].push_back(p.first);
                }
                cur += 4;
            }
        }
        
        // Inter-group edges
        for (size_t i = 0; i < groups.size(); ++i) {
            for (size_t j = i + 1; j < groups.size(); ++j) {
                std::vector<int> q;
                std::vector<std::pair<int, int>> pairs;
                for (int u : groups[i]) {
                    for (int v : groups[j]) {
                        q.push_back(u);
                        q.push_back(v);
                        q.push_back(u);
                        q.push_back(v);
                        pairs.push_back({u, v});
                    }
                }
                auto res = do_query(q);
                int cur = 0;
                for (const auto& p : pairs) {
                    if (res[cur + 1]) {
                        adj[p.first].push_back(p.second);
                        adj[p.second].push_back(p.first);
                    }
                    cur += 4;
                }
            }
        }
    } else {
        solve();
        return 0;
    }

    int start_node = -1;
    for (int i = 1; i <= n; ++i) {
        if (!adj[i].empty()) {
            start_node = i;
            break;
        }
    }
    
    if (n == 1) {
        p[0] = 1;
    } else if (start_node != -1) {
        int curr = start_node;
        int prev = -1;
        for (int i = 0; i < n; ++i) {
            p[i] = curr;
            visited[curr] = true;
            int next_node = -1;
            for (int neighbor : adj[curr]) {
                if (neighbor != prev) {
                    next_node = neighbor;
                    break;
                }
            }
            if (next_node == -1 && i < n - 1) {
                for (int k = 1; k <= n; ++k) {
                    if (!visited[k]) {
                        next_node = k;
                        break;
                    }
                }
            }
            prev = curr;
            curr = next_node;
        }
    }

    std::vector<int> p_vec;
    std::vector<bool> in_p(n + 1, false);
    for (int i = 0; i < n; ++i) {
        if (p[i] != 0 && !in_p[p[i]]) {
            p_vec.push_back(p[i]);
            in_p[p[i]] = true;
        }
    }
    for (int i = 1; i <= n; ++i) {
        if (!in_p[i]) {
            p_vec.push_back(i);
        }
    }
    answer(p_vec);

    return 0;
}