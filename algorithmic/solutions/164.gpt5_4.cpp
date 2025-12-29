#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> stacks(m);
    vector<pair<int,int>> pos(n + 1, {-1, -1}); // pos[v] = {stack_index, index_from_bottom}
    int h = n / m;
    for (int i = 0; i < m; ++i) {
        stacks[i].reserve(n);
        for (int j = 0; j < h; ++j) {
            int x; cin >> x;
            stacks[i].push_back(x);
            pos[x] = {i, j};
        }
    }

    vector<pair<int,int>> ops;

    auto choose_dest = [&](int s)->int{
        int best = -1;
        int bestH = INT_MAX;
        for (int i = 0; i < m; ++i) {
            if (i == s) continue;
            int hi = (int)stacks[i].size();
            if (hi < bestH) {
                bestH = hi;
                best = i;
            }
        }
        if (best == -1) best = (s + 1) % m; // fallback (shouldn't happen for given constraints)
        return best;
    };

    auto move_chunk = [&](int v, int dest){
        auto [s, idx] = pos[v];
        int h1 = (int)stacks[s].size();
        vector<int> chunk;
        chunk.reserve(h1 - idx);
        for (int k = idx; k < h1; ++k) chunk.push_back(stacks[s][k]);
        stacks[s].resize(idx);
        int destsize = (int)stacks[dest].size();
        for (int l = 0; l < (int)chunk.size(); ++l) {
            int x = chunk[l];
            stacks[dest].push_back(x);
            pos[x] = {dest, destsize + l};
        }
        ops.emplace_back(v, dest + 1);
    };

    for (int v = 1; v <= n; ++v) {
        auto [s, idx] = pos[v];
        if (idx != (int)stacks[s].size() - 1) {
            int u = stacks[s][idx + 1]; // box directly above v
            int dest = choose_dest(s);
            move_chunk(u, dest);
        }
        // now v is at the top
        ops.emplace_back(v, 0);
        stacks[s].pop_back();
        pos[v] = {-1, -1};
    }

    for (auto &p : ops) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}