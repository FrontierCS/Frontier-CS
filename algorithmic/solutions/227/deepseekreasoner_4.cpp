#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        cin >> p[i];
    }

    // last values for the four subsequences:
    // 0: a (increasing), 1: b (decreasing), 2: c (increasing), 3: d (decreasing)
    vector<int> last(4);
    last[0] = last[2] = 0;          // smaller than any value in permutation
    last[1] = last[3] = n + 1;      // larger than any value in permutation

    vector<vector<int>> seq(4);

    for (int x : p) {
        vector<int> inc_cand, dec_cand;
        // increasing candidates (indices 0 and 2)
        for (int i : {0, 2}) {
            if (last[i] < x) inc_cand.push_back(i);
        }
        // decreasing candidates (indices 1 and 3)
        for (int i : {1, 3}) {
            if (last[i] > x) dec_cand.push_back(i);
        }

        int chosen = -1;

        if (!inc_cand.empty() && !dec_cand.empty()) {
            // choose best increasing candidate: largest last < x
            int best_inc = inc_cand[0];
            for (int i : inc_cand) {
                if (last[i] > last[best_inc]) best_inc = i;
            }
            // choose best decreasing candidate: smallest last > x
            int best_dec = dec_cand[0];
            for (int i : dec_cand) {
                if (last[i] < last[best_dec]) best_dec = i;
            }
            int gap_inc = x - last[best_inc];
            int gap_dec = last[best_dec] - x;
            if (gap_inc <= gap_dec) {
                chosen = best_inc;
            } else {
                chosen = best_dec;
            }
        } else if (!inc_cand.empty()) {
            int best_inc = inc_cand[0];
            for (int i : inc_cand) {
                if (last[i] > last[best_inc]) best_inc = i;
            }
            chosen = best_inc;
        } else if (!dec_cand.empty()) {
            int best_dec = dec_cand[0];
            for (int i : dec_cand) {
                if (last[i] < last[best_dec]) best_dec = i;
            }
            chosen = best_dec;
        } else {
            // no candidate maintains monotonicity; pick the slot that gives the largest "improvement"
            vector<pair<int, int>> improvement;
            for (int i : {0, 2}) {
                improvement.emplace_back(i, last[i] - x);   // for increasing slots (last >= x)
            }
            for (int i : {1, 3}) {
                improvement.emplace_back(i, x - last[i]);   // for decreasing slots (last <= x)
            }
            int best = 0;
            for (int i = 1; i < 4; ++i) {
                if (improvement[i].second > improvement[best].second) {
                    best = i;
                }
            }
            chosen = improvement[best].first;
        }

        seq[chosen].push_back(x);
        last[chosen] = x;
    }

    // Output
    cout << seq[0].size() << " " << seq[1].size() << " " << seq[2].size() << " " << seq[3].size() << "\n";
    for (int i = 0; i < 4; ++i) {
        for (size_t j = 0; j < seq[i].size(); ++j) {
            if (j > 0) cout << " ";
            cout << seq[i][j];
        }
        cout << "\n";
    }

    return 0;
}