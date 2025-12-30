#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<string> patterns(m);
    for (int i = 0; i < m; ++i) {
        cin >> patterns[i];
    }

    // letter_group[i][j] = 0 for '?', 1 for 'A', 2 for 'C', 3 for 'G', 4 for 'T'
    vector<vector<char>> letter_group(m, vector<char>(n, 0));
    vector<int> mask_q(n, 0);
    vector<array<int, 5>> mask_letter(n); // indices 1..4 used for A,C,G,T

    for (int j = 0; j < n; ++j) {
        for (int i = 0; i < m; ++i) {
            char c = patterns[i][j];
            char val;
            if (c == '?') val = 0;
            else if (c == 'A') val = 1;
            else if (c == 'C') val = 2;
            else if (c == 'G') val = 3;
            else if (c == 'T') val = 4;
            else val = 0; // should not happen
            letter_group[i][j] = val;
            if (val == 0) {
                mask_q[j] |= (1 << i);
            } else {
                mask_letter[j][val] |= (1 << i);
            }
        }
    }

    int total_masks = 1 << m;
    vector<char> compatible(total_masks, 1);
    vector<int> cnt(total_masks, 0);
    vector<int> popcount(total_masks);
    for (int mask = 0; mask < total_masks; ++mask) {
        popcount[mask] = __builtin_popcount(mask);
    }

    vector<int> active(total_masks);
    iota(active.begin(), active.end(), 0);

    for (int j = 0; j < n; ++j) {
        int mq = mask_q[j];
        array<int, 5>& ml = mask_letter[j];
        vector<int> next_active;
        next_active.reserve(active.size());
        for (int mask : active) {
            int concrete = mask & ~mq;
            if (concrete == 0) {
                cnt[mask]++;
                next_active.push_back(mask);
            } else {
                int i = __builtin_ctz(concrete);
                char L = letter_group[i][j]; // L is in {1,2,3,4}
                if ((concrete & ~ml[L]) == 0) {
                    next_active.push_back(mask);
                } else {
                    compatible[mask] = 0;
                }
            }
        }
        active.swap(next_active);
    }

    long double prob = 0.0L;
    for (int mask = 1; mask < total_masks; ++mask) {
        if (!compatible[mask]) continue;
        int sign = (popcount[mask] & 1) ? 1 : -1;
        long double term = powl(4.0L, cnt[mask] - n);
        prob += sign * term;
    }

    cout << fixed << setprecision(15) << prob << endl;
    return 0;
}