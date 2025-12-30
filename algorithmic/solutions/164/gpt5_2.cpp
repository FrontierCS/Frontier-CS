#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> stacks(m);
    int h0 = n / m;
    vector<pair<int,int>> pos(n + 1, {-1, -1}); // pos[v] = {stack, index from bottom}

    for (int i = 0; i < m; i++) {
        stacks[i].resize(h0);
        for (int j = 0; j < h0; j++) {
            int x; cin >> x;
            stacks[i][j] = x;
            pos[x] = {i, j};
        }
    }

    vector<pair<int,int>> ops;
    ops.reserve(2 * n + 10);

    auto find_dest = [&](int s) -> int {
        int dest = -1;
        int minsize = INT_MAX;
        for (int i = 0; i < m; i++) {
            if (i == s) continue;
            int sz = (int)stacks[i].size();
            if (sz < minsize) {
                minsize = sz;
                dest = i;
            }
        }
        if (dest == -1) dest = (s + 1) % m;
        return dest;
    };

    for (int v = 1; v <= n; v++) {
        auto p = pos[v];
        int s = p.first;
        int idx = p.second;
        if (s == -1) continue; // already removed (shouldn't happen in this flow)

        if (idx != (int)stacks[s].size() - 1) {
            int w = stacks[s][idx + 1];
            int dest = find_dest(s);
            ops.push_back({w, dest + 1});

            int start = idx + 1;
            int len = (int)stacks[s].size() - start;
            vector<int> moved;
            moved.reserve(len);
            for (int t = start; t < (int)stacks[s].size(); t++) moved.push_back(stacks[s][t]);
            stacks[s].resize(start);

            int destStart = (int)stacks[dest].size();
            stacks[dest].insert(stacks[dest].end(), moved.begin(), moved.end());
            for (int t = 0; t < len; t++) {
                int x = moved[t];
                pos[x] = {dest, destStart + t};
            }
        }

        // Now carry out v
        s = pos[v].first;
        idx = pos[v].second;
        if (idx != (int)stacks[s].size() - 1) {
            // Fallback (shouldn't happen): keep moving chunks above v until it's top
            while (idx != (int)stacks[s].size() - 1) {
                int w = stacks[s][idx + 1];
                int dest = find_dest(s);
                if (dest == s) dest = (s + 1) % m;
                ops.push_back({w, dest + 1});
                int start = idx + 1;
                int len = (int)stacks[s].size() - start;
                vector<int> moved;
                moved.reserve(len);
                moved.insert(moved.end(), stacks[s].begin() + start, stacks[s].end());
                stacks[s].resize(start);
                int destStart = (int)stacks[dest].size();
                stacks[dest].insert(stacks[dest].end(), moved.begin(), moved.end());
                for (int t = 0; t < len; t++) {
                    int x = moved[t];
                    pos[x] = {dest, destStart + t};
                }
                idx = pos[v].second;
            }
        }
        ops.push_back({v, 0});
        stacks[s].pop_back();
        pos[v] = {-1, -1};
    }

    for (auto &pr : ops) {
        cout << pr.first << " " << pr.second << "\n";
    }

    return 0;
}