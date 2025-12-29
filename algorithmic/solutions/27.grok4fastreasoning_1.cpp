#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    bool swapped = (n > m);
    int s = swapped ? m : n;
    int l = swapped ? n : m;
    vector<vector<int>> col_rows(l + 1);
    vector<vector<char>> placed(s + 1, vector<char>(l + 1, 0));
    vector<vector<int>> interr(s + 1, vector<int>(s + 1, 0));
    vector<pair<int, int>> points;
    auto try_add = [&](int r, int c) -> void {
        if (c < 1 || c > l || placed[r][c]) return;
        const auto& lst = col_rows[c];
        bool can = true;
        for (int pr : lst) {
            if (interr[r][pr] >= 1) {
                can = false;
                break;
            }
        }
        if (can) {
            placed[r][c] = 1;
            for (int pr : lst) {
                interr[r][pr]++;
                interr[pr][r]++;
            }
            col_rows[c].push_back(r);
            points.emplace_back(r, c);
        }
    };
    for (int delta = 0; delta <= l; ++delta) {
        for (int r = 1; r <= s; ++r) {
            // positive
            int c = r + delta;
            try_add(r, c);
            // negative
            c = r - delta;
            try_add(r, c);
        }
    }
    cout << points.size() << endl;
    if (!swapped) {
        for (auto [rr, cc] : points) {
            cout << rr << " " << cc << endl;
        }
    } else {
        for (auto [abstr, univ] : points) {
            cout << univ << " " << abstr << endl;
        }
    }
    return 0;
}