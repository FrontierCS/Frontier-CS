#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <map>

int n;
std::vector<int> p1, p2;
std::map<int, int> parent;

int ask_query(const std::vector<int>& s) {
    if (s.empty()) {
        return 0;
    }
    std::cout << "? " << s.size() << std::endl;
    for (size_t i = 0; i < s.size(); ++i) {
        std::cout << s[i] << (i == s.size() - 1 ? "" : " ");
    }
    std::cout << std::endl;
    int m;
    std::cin >> m;
    if (m == -1) exit(0);
    return m;
}

int find_neighbor(int u, const std::vector<int>& S) {
    if (S.empty()) {
        return -1;
    }
    std::vector<int> cand = S;
    while (cand.size() > 1) {
        std::vector<int> L, R;
        for (size_t i = 0; i < cand.size() / 2; ++i) L.push_back(cand[i]);
        for (size_t i = cand.size() / 2; i < cand.size(); ++i) R.push_back(cand[i]);
        
        std::vector<int> u_L = L;
        u_L.push_back(u);
        
        if (ask_query(u_L) - ask_query(L) > 0) {
            cand = L;
        } else {
            cand = R;
        }
    }
    return cand[0];
}

void report_bipartite() {
    std::cout << "Y " << p1.size() << std::endl;
    for (size_t i = 0; i < p1.size(); ++i) {
        std::cout << p1[i] << (i == p1.size() - 1 ? "" : " ");
    }
    std::cout << std::endl;
}

void report_odd_cycle(int u, int v1, int v2) {
    std::vector<int> path1_rev;
    int curr = v1;
    while (curr != 0) {
        path1_rev.push_back(curr);
        curr = parent[curr];
    }

    std::vector<int> path2_rev;
    curr = v2;
    while (curr != 0) {
        path2_rev.push_back(curr);
        curr = parent[curr];
    }

    std::set<int> path1_nodes(path1_rev.begin(), path1_rev.end());
    int w = -1;
    for (int node : path2_rev) {
        if (path1_nodes.count(node)) {
            w = node;
            break;
        }
    }

    std::vector<int> cycle;
    cycle.push_back(u);
    
    for (int node : path1_rev) {
        cycle.push_back(node);
        if (node == w) break;
    }

    size_t w_idx_p2 = 0;
    for(size_t i = 0; i < path2_rev.size(); ++i) {
        if (path2_rev[i] == w) {
            w_idx_p2 = i;
            break;
        }
    }

    for (int i = w_idx_p2 - 1; i >= 0; --i) {
        cycle.push_back(path2_rev[i]);
    }

    std::cout << "N " << cycle.size() << std::endl;
    for (size_t i = 0; i < cycle.size(); ++i) {
        std::cout << cycle[i] << (i == cycle.size() - 1 ? "" : " ");
    }
    std::cout << std::endl;
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;

    p1.push_back(1);
    parent[1] = 0;

    std::set<int> uncolored;
    for (int i = 2; i <= n; ++i) {
        uncolored.insert(i);
    }

    while (p1.size() + p2.size() < n) {
        std::vector<int> C;
        C.insert(C.end(), p1.begin(), p1.end());
        C.insert(C.end(), p2.begin(), p2.end());
        int e_C = ask_query(C);

        std::vector<int> U_vec(uncolored.begin(), uncolored.end());
        std::vector<int> U_cand = U_vec;

        while (U_cand.size() > 1) {
            std::vector<int> L, R;
            for (size_t i = 0; i < U_cand.size() / 2; ++i) L.push_back(U_cand[i]);
            for (size_t i = U_cand.size() / 2; i < U_cand.size(); ++i) R.push_back(U_cand[i]);
            
            std::vector<int> C_L = C;
            C_L.insert(C_L.end(), L.begin(), L.end());
            
            if (ask_query(C_L) - e_C - ask_query(L) > 0) {
                U_cand = L;
            } else {
                U_cand = R;
            }
        }
        int u = U_cand[0];
        uncolored.erase(u);

        bool conn_p1, conn_p2;
        
        std::vector<int> p1_u = p1; p1_u.push_back(u);
        conn_p1 = (ask_query(p1_u) - ask_query(p1) > 0);

        std::vector<int> p2_u = p2; p2_u.push_back(u);
        conn_p2 = (ask_query(p2_u) - ask_query(p2) > 0);
        
        if (conn_p1 && conn_p2) {
            int v1 = find_neighbor(u, p1);
            int v2 = find_neighbor(u, p2);
            report_odd_cycle(u, v1, v2);
            return 0;
        }

        if (conn_p1) {
            p2.push_back(u);
            parent[u] = find_neighbor(u, p1);
        } else {
            p1.push_back(u);
            parent[u] = find_neighbor(u, p2);
        }
    }

    report_bipartite();

    return 0;
}