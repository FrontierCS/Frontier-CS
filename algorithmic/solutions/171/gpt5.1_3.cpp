#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<pair<int,int>> p(M);
    for (int k = 0; k < M; ++k) {
        cin >> p[k].first >> p[k].second;
    }

    const int LIMIT = 2 * N * M;
    vector<pair<char,char>> actions;
    actions.reserve(LIMIT);

    int cur_i = p[0].first;
    int cur_j = p[0].second;

    bool full = false;

    for (int k = 1; k < M && !full; ++k) {
        int ti = p[k].first;
        int tj = p[k].second;

        while (cur_i != ti && !full) {
            if ((int)actions.size() >= LIMIT) { full = true; break; }
            if (ti > cur_i) {
                actions.emplace_back('M', 'D');
                cur_i++;
            } else {
                actions.emplace_back('M', 'U');
                cur_i--;
            }
        }
        while (cur_j != tj && !full) {
            if ((int)actions.size() >= LIMIT) { full = true; break; }
            if (tj > cur_j) {
                actions.emplace_back('M', 'R');
                cur_j++;
            } else {
                actions.emplace_back('M', 'L');
                cur_j--;
            }
        }
    }

    for (auto &ac : actions) {
        cout << ac.first << ' ' << ac.second << '\n';
    }

    return 0;
}