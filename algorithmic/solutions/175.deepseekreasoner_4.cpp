#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    scanf("%d %d", &n, &m);
    vector<array<int,3>> clause_var(m);
    vector<array<bool,3>> clause_sign(m);
    vector<vector<pair<int,bool>>> occs(n); // (clause_id, is_positive)

    for (int i = 0; i < m; ++i) {
        for (int k = 0; k < 3; ++k) {
            int val;
            scanf("%d", &val);
            int var = abs(val) - 1;
            bool sign = (val > 0);
            clause_var[i][k] = var;
            clause_sign[i][k] = sign;
            occs[var].push_back({i, sign});
        }
    }

    if (m == 0) {
        for (int i = 0; i < n; ++i) printf("0 ");
        printf("\n");
        return 0;
    }

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> rand_bit(0, 1);
    uniform_real_distribution<double> rand_prob(0.0, 1.0);

    const int NUM_RESTARTS = 3;
    const int MAX_PASSES = 10;
    const double PROB_FLIP_ZERO = 0.001;

    double best_score = -1.0;
    vector<bool> best_assn(n);

    for (int restart = 0; restart < NUM_RESTARTS; ++restart) {
        vector<bool> assn(n);
        for (int i = 0; i < n; ++i) assn[i] = rand_bit(rng);

        vector<int> sat(m, 0);
        int total_sat = 0;
        for (int i = 0; i < m; ++i) {
            int cnt = 0;
            for (int k = 0; k < 3; ++k) {
                int var = clause_var[i][k];
                bool sign = clause_sign[i][k];
                if ((assn[var] && sign) || (!assn[var] && !sign))
                    ++cnt;
            }
            sat[i] = cnt;
            if (cnt > 0) ++total_sat;
        }

        for (int pass = 0; pass < MAX_PASSES; ++pass) {
            vector<int> order(n);
            iota(order.begin(), order.end(), 0);
            shuffle(order.begin(), order.end(), rng);

            for (int idx : order) {
                bool old_val = assn[idx];
                bool new_val = !old_val;
                int delta = 0;

                for (auto [cid, pos] : occs[idx]) {
                    bool old_lit_true = (old_val == pos);
                    bool new_lit_true = (new_val == pos);
                    int sc = sat[cid];
                    if (sc == 0 && new_lit_true) ++delta;
                    else if (sc == 1 && old_lit_true && !new_lit_true) --delta;
                }

                bool flip = false;
                if (delta > 0) flip = true;
                else if (delta == 0 && rand_prob(rng) < PROB_FLIP_ZERO) flip = true;

                if (flip) {
                    total_sat += delta;
                    for (auto [cid, pos] : occs[idx]) {
                        bool old_lit_true = (old_val == pos);
                        bool new_lit_true = (new_val == pos);
                        if (old_lit_true && !new_lit_true) --sat[cid];
                        else if (!old_lit_true && new_lit_true) ++sat[cid];
                    }
                    assn[idx] = new_val;
                }
            }
        }

        double score = (double)total_sat / m;
        if (score > best_score) {
            best_score = score;
            best_assn = assn;
        }
    }

    for (int i = 0; i < n; ++i) {
        printf("%d ", best_assn[i] ? 1 : 0);
    }
    printf("\n");

    return 0;
}