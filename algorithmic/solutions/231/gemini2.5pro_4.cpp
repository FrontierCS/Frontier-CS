#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <set>

using namespace std;

void solve() {
    int n, m, t;
    if (!(cin >> n >> m >> t)) return;

    set<pair<int, int>> initial_edges;
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
    }

    vector<pair<char, pair<int, int>>> modifications;
    
    // Gadget vertices
    // b_k (bit sinks): 991-1000
    // i_i (high bits collectors): 959-990
    // j_j (low bits collectors): 927-958
    // s_k (selectors): 891-900
    
    // For each bit k, create a cycle gadget s_k -> b_k -> s_k
    for (int k = 0; k < 10; ++k) {
        modifications.push_back({'+', {891 + k, 991 + k}});
        modifications.push_back({'+', {991 + k, 891 + k}});
    }

    // Connect i_i collectors to selectors s_k
    for (int i = 0; i < 32; ++i) {
        for (int k = 5; k < 10; ++k) {
            if ((i >> (k - 5)) & 1) {
                modifications.push_back({'+', {959 + i, 891 + k}});
            }
        }
    }

    // Connect j_j collectors to selectors s_k
    for (int j = 0; j < 32; ++j) {
        for (int k = 0; k < 5; ++k) {
            if ((j >> k) & 1) {
                modifications.push_back({'+', {927 + j, 891 + k}});
            }
        }
    }
    
    vector<vector<int>> u_to_i_groups(32);
    vector<vector<int>> u_to_j_groups(32);

    for (int u = 1; u <= 890; ++u) {
        int val = u - 1;
        u_to_i_groups[val / 32].push_back(u);
        u_to_j_groups[val % 32].push_back(u);
    }
    
    for (int i = 0; i < 32; ++i) {
        if (u_to_i_groups[i].empty()) continue;
        for (size_t k = 0; k < u_to_i_groups[i].size() - 1; ++k) {
             modifications.push_back({'+', {u_to_i_groups[i][k], u_to_i_groups[i][k+1]}});
        }
        modifications.push_back({'+', {u_to_i_groups[i].back(), 959 + i}});
    }

    for (int j = 0; j < 32; ++j) {
        if (u_to_j_groups[j].empty()) continue;
        for (size_t k = 0; k < u_to_j_groups[j].size() - 1; ++k) {
            modifications.push_back({'+', {u_to_j_groups[j][k], u_to_j_groups[j][k+1]}});
        }
        modifications.push_back({'+', {u_to_j_groups[j].back(), 927 + j}});
    }

    cout << modifications.size() << endl;
    for (const auto& mod : modifications) {
        cout << mod.first << " " << mod.second.first << " " << mod.second.second << endl;
    }
    cout.flush();

    for (int round = 0; round < t; ++round) {
        int v_minus_1 = 0;
        for (int k = 0; k < 10; ++k) {
            cout << "? 1 " << 891 + k << endl;
            cout.flush();
            string resp;
            cin >> resp;
            if (resp == "Draw") {
                v_minus_1 |= (1 << k);
            }
        }
        cout << "! " << v_minus_1 + 1 << endl;
        cout.flush();
        string final_resp;
        cin >> final_resp;
        if (final_resp[0] == 'W') {
            fflush(stdout);
            return;
        };
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}