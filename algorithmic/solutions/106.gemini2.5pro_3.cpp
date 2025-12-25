#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

// I/O and query utilities
int n;
std::map<std::vector<int>, int> memo;

int ask(std::vector<int> s) {
    if (s.empty()) {
        return 0;
    }
    std::sort(s.begin(), s.end());
    s.erase(std::unique(s.begin(), s.end()), s.end());
    if (memo.count(s)) {
        return memo[s];
    }
    std::cout << "? " << s.size() << std::endl;
    for (size_t i = 0; i < s.size(); ++i) {
        std::cout << s[i] << (i == s.size() - 1 ? "" : " ");
    }
    std::cout << std::endl;
    int m;
    std::cin >> m;
    if (m == -1) exit(0);
    return memo[s] = m;
}

std::vector<int> set_union(const std::vector<int>& A, const std::vector<int>& B) {
    std::vector<int> res = A;
    res.insert(res.end(), B.begin(), B.end());
    return res;
}

int deg_vertex_set(int v, const std::vector<int>& S) {
    if (S.empty()) return 0;
    auto S_with_v = S;
    S_with_v.push_back(v);
    return ask(S_with_v) - ask(S);
}

int deg_set_set(const std::vector<int>& S1, const std::vector<int>& S2) {
    if (S1.empty() || S2.empty()) return 0;
    return ask(set_union(S1, S2)) - ask(S1) - ask(S2);
}

// Graph properties
int parent[601];
int color[601];
int depth[601];

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;

    if (n == 1) {
        std::cout << "Y 1" << std::endl;
        std::cout << 1 << std::endl;
        return 0;
    }

    std::vector<int> V_in_vec;
    std::vector<bool> in_V_in(n + 1, false);

    V_in_vec.push_back(1);
    in_V_in[1] = true;
    parent[1] = 0;
    color[1] = 0;
    depth[1] = 0;

    while (V_in_vec.size() < n) {
        std::vector<int> V_out_vec;
        for (int j = 1; j <= n; ++j) {
            if (!in_V_in[j]) {
                V_out_vec.push_back(j);
            }
        }
        
        int l = 0, r = V_out_vec.size() - 1;
        while(l < r) {
            int mid = l + (r - l) / 2;
            std::vector<int> S_test;
            for(int k = l; k <= mid; ++k) S_test.push_back(V_out_vec[k]);
            if (deg_set_set(V_in_vec, S_test) > 0) {
                r = mid;
            } else {
                l = mid + 1;
            }
        }
        int v = V_out_vec[l];

        l = 0, r = V_in_vec.size() - 1;
        while (l < r) {
            int mid = l + (r - l) / 2;
            std::vector<int> S_test;
            for (int k = l; k <= mid; ++k) S_test.push_back(V_in_vec[k]);
            if (deg_vertex_set(v, S_test) > 0) {
                r = mid;
            } else {
                l = mid + 1;
            }
        }
        int u = V_in_vec[l];

        parent[v] = u;
        depth[v] = depth[u] + 1;
        color[v] = 1 - color[u];
        V_in_vec.push_back(v);
        in_V_in[v] = true;
    }

    std::vector<int> C0, C1;
    for (int i = 1; i <= n; ++i) {
        if (color[i] == 0) C0.push_back(i);
        else C1.push_back(i);
    }

    int C0_edges = ask(C0);
    int C1_edges = C0_edges > 0 ? 0 : ask(C1);

    if (C0_edges == 0 && C1_edges == 0) {
        std::cout << "Y " << C0.size() << std::endl;
        for (size_t i = 0; i < C0.size(); ++i) {
            std::cout << C0[i] << (i == C0.size() - 1 ? "" : " ");
        }
        std::cout << std::endl;
    } else {
        std::vector<int> problem_set = C0_edges > 0 ? C0 : C1;
        int u = -1, v = -1;
        
        for(size_t i = 0; i < problem_set.size(); ++i) {
            int current_node = problem_set[i];
            std::vector<int> rest_of_set;
            for(size_t j = i + 1; j < problem_set.size(); ++j) {
                rest_of_set.push_back(problem_set[j]);
            }
            if (!rest_of_set.empty() && deg_vertex_set(current_node, rest_of_set) > 0) {
                u = current_node;
                
                int l = 0, r = rest_of_set.size() - 1;
                while(l < r) {
                    int mid = l + (r-l)/2;
                    std::vector<int> S_test;
                    for(int k=l; k<=mid; ++k) S_test.push_back(rest_of_set[k]);
                    if (deg_vertex_set(u, S_test) > 0) {
                        r = mid;
                    } else {
                        l = mid+1;
                    }
                }
                v = rest_of_set[l];
                break;
            }
        }

        std::vector<int> path_u_rev, path_v_rev;
        int curr = u;
        while (curr != 0) {
            path_u_rev.push_back(curr);
            curr = parent[curr];
        }
        curr = v;
        while (curr != 0) {
            path_v_rev.push_back(curr);
            curr = parent[curr];
        }
        std::vector<int> path_u = path_u_rev; std::reverse(path_u.begin(), path_u.end());
        std::vector<int> path_v = path_v_rev; std::reverse(path_v.begin(), path_v.end());

        int lca_depth = 0;
        while (lca_depth < path_u.size() && lca_depth < path_v.size() && path_u[lca_depth] == path_v[lca_depth]) {
            lca_depth++;
        }
        lca_depth--;

        std::vector<int> cycle;
        for (size_t i = path_u.size() - 1; i > lca_depth; --i) {
            cycle.push_back(path_u[i]);
        }
        for (size_t i = lca_depth; i < path_v.size(); ++i) {
            cycle.push_back(path_v[i]);
        }
        
        std::cout << "N " << cycle.size() << std::endl;
        for(size_t i=0; i<cycle.size(); ++i) {
            std::cout << cycle[i] << (i == cycle.size()-1 ? "" : " ");
        }
        std::cout << std::endl;
    }

    return 0;
}