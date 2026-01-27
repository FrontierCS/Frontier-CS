#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if(!(cin >> N >> M)) return 0;
    int si, sj;
    cin >> si >> sj;
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];
    vector<string> t(M);
    for (int k = 0; k < M; ++k) cin >> t[k];

    // Positions for each letter
    vector<vector<pair<int,int>>> pos(26);
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            pos[grid[i][j]-'A'].push_back({i,j});

    // Build graph of 4-grams
    unordered_map<string,int> id;
    vector<string> id2str;
    auto get_id = [&](const string &s)->int{
        auto it = id.find(s);
        if (it != id.end()) return it->second;
        int nid = (int)id.size();
        id[s] = nid;
        id2str.push_back(s);
        return nid;
    };

    int E = 0;
    // adjacency lists
    vector<vector<pair<int,char>>> adj; // to, last char
    for (int k = 0; k < M; ++k) {
        string u4 = t[k].substr(0,4);
        string v4 = t[k].substr(1,4);
        int u = get_id(u4);
        int v = get_id(v4);
        if ((int)adj.size() <= max(u,v)) adj.resize(max(u,v)+1);
        adj[u].push_back({v, t[k][4]});
        ++E;
    }
    if ((int)adj.size() < (int)id2str.size()) adj.resize(id2str.size());

    string S;
    // Perform Eulerian traversals for all components
    for (int start = 0; start < (int)adj.size(); ++start) {
        if (adj[start].empty()) continue;
        // Start new component traversal at this node
        // Append starting 4-gram (bridge between components simply by adding these 4 chars)
        S += id2str[start];

        vector<int> st;
        vector<char> chst;
        st.push_back(start);
        while (!st.empty()) {
            int u = st.back();
            if (!adj[u].empty()) {
                auto e = adj[u].back(); adj[u].pop_back();
                st.push_back(e.first);
                chst.push_back(e.second);
            } else {
                st.pop_back();
                if (!chst.empty()) {
                    S.push_back(chst.back());
                    chst.pop_back();
                }
            }
        }
    }

    // If somehow no edges were present (shouldn't happen with M=200), create a small string
    if (S.empty()) {
        // Just type a few letters to be safe
        S = "ABCDE";
    }

    // Plan movements: greedily pick nearest occurrence for each letter
    vector<pair<int,int>> ops;
    ops.reserve(S.size());
    int ci = si, cj = sj;
    for (char ch : S) {
        int c = ch - 'A';
        const auto &lst = pos[c];
        // choose nearest by Manhattan distance
        int bestd = INT_MAX;
        pair<int,int> bestp = lst[0];
        for (auto &p : lst) {
            int d = abs(p.first - ci) + abs(p.second - cj);
            if (d < bestd) {
                bestd = d;
                bestp = p;
            }
        }
        ops.push_back(bestp);
        ci = bestp.first;
        cj = bestp.second;
    }

    // Output operations
    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}