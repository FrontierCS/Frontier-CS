#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> poles(n + 2);
    for (int i = 1; i <= n; ++i) {
        poles[i].resize(m);
        for (int j = 0; j < m; ++j) {
            cin >> poles[i][j];
        }
    }
    vector<int> tgt(n + 1);
    for (int i = 1; i <= n; ++i) tgt[i] = i;
    vector<int> wrong(n + 2, 0);
    for (int i = 1; i <= n; ++i) {
        for (int b : poles[i]) {
            if (b != i) ++wrong[i];
        }
    }
    vector<pair<int, int>> moves;
    auto is_done = [&]() -> bool {
        for (int c = 1; c <= n; ++c) {
            int y = tgt[c];
            if (wrong[y] != 0 || poles[y].size() != static_cast<size_t>(m)) return false;
        }
        return true;
    };
    int max_ops = 2000010;
    while (!is_done() && static_cast<int>(moves.size()) < max_ops) {
        bool moved = false;
        // useful moves
        for (int x = 1; x <= n + 1; ++x) {
            if (poles[x].empty()) continue;
            int b = poles[x].back();
            int y = tgt[b];
            if (x == y) continue;
            if (poles[y].size() < static_cast<size_t>(m) && (poles[y].empty() || poles[y].back() == b)) {
                moves.emplace_back(x, y);
                poles[y].push_back(b);
                poles[x].pop_back();
                if (x >= 1 && x <= n && b != x) --wrong[x];
                if (y >= 1 && y <= n && b != y) ++wrong[y];
                moved = true;
                break;
            }
        }
        if (moved) continue;
        // cleaning impure targets
        for (int y = 1; y <= n; ++y) {
            if (wrong[y] == 0 || poles[y].empty()) continue;
            int b = poles[y].back();
            int z = -1;
            if (n + 1 != y && poles[n + 1].size() < static_cast<size_t>(m)) {
                z = n + 1;
            } else {
                for (int k = 1; k <= n + 1; ++k) {
                    if (k != y && poles[k].size() < static_cast<size_t>(m)) {
                        z = k;
                        break;
                    }
                }
            }
            if (z != -1) {
                moves.emplace_back(y, z);
                poles[z].push_back(b);
                poles[y].pop_back();
                if (y >= 1 && y <= n && b != y) --wrong[y];
                if (z >= 1 && z <= n && b != z) ++wrong[z];
                moved = true;
                break;
            }
        }
        if (moved) continue;
        // general preparatory
        if (poles[n + 1].size() < static_cast<size_t>(m)) {
            int x = -1;
            for (int cand = 1; cand <= n; ++cand) {
                if (poles[cand].empty()) continue;
                int bb = poles[cand].back();
                int ty = tgt[bb];
                if (cand == ty && bb == ty) continue;
                x = cand;
                break;
            }
            if (x != -1) {
                int b = poles[x].back();
                moves.emplace_back(x, n + 1);
                poles[n + 1].push_back(b);
                poles[x].pop_back();
                if (x >= 1 && x <= n && b != x) --wrong[x];
                moved = true;
            }
        }
        if (!moved && !poles[n + 1].empty()) {
            int b = poles[n + 1].back();
            int z = -1;
            for (int cand = 1; cand <= n; ++cand) {
                if (poles[cand].size() < static_cast<size_t>(m)) {
                    if (z == -1 || poles[cand].empty() || poles[cand].back() == b) {
                        z = cand;
                    }
                }
            }
            if (z != -1) {
                moves.emplace_back(n + 1, z);
                poles[z].push_back(b);
                poles[n + 1].pop_back();
                if (z >= 1 && z <= n && b != z) ++wrong[z];
                moved = true;
            }
        }
        if (!moved) {
            break;
        }
    }
    cout << moves.size() << endl;
    for (auto [x, y] : moves) {
        cout << x << " " << y << endl;
    }
    return 0;
}