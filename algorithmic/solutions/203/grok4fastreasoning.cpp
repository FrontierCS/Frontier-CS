#include <bits/stdc++.h>
using namespace std;

int compute_delta(int L, int R, int C) {
    int Ap = !(L && !R);
    int t1 = Ap * (1 - C);
    int t2 = (1 - L) * R;
    return t1 - t2;
}

void rec(int bb, int curr_r, int curr_c, int li, vector<tuple<int, int, int>>& cand, const vector<int>& observed, int N) {
    if (bb == 9) {
        int ri = curr_r;
        int ci = curr_c;
        if (ri >= 0 && ri < N && ci >= 0 && ci < N && ri != li && ci != li && ci != ri) {
            cand.emplace_back(li, ri, ci);
        }
        return;
    }
    int Lb = (li >> bb) & 1;
    int obs = observed[bb];
    set<pair<int, int>> poss_set;
    for (int Rb = 0; Rb < 2; Rb++) {
        for (int Cb = 0; Cb < 2; Cb++) {
            int exp = compute_delta(Lb, Rb, Cb);
            if (exp == obs) {
                poss_set.emplace(Rb, Cb);
            }
        }
    }
    vector<pair<int, int>> poss(poss_set.begin(), poss_set.end());
    for (auto [Rb, Cb] : poss) {
        rec(bb + 1, curr_r | (Rb << bb), curr_c | (Cb << bb), li, cand, observed, N);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    cin >> N;
    vector<pair<int, int>> pairs(N);
    for (int ai = 1; ai <= N; ++ai) {
        int a = ai;
        vector<vector<int>> all_V(17);
        for (int q = 0; q < 9; ++q) {
            vector<int> v;
            for (int i = 0; i < N; ++i) {
                if ((i & (1 << q)) != 0) {
                    v.push_back(N + 1 + i);
                }
            }
            all_V[q] = v;
        }
        for (int q = 9; q < 17; ++q) {
            int off = q - 9;
            vector<int> v;
            int frac = N * (off + 1) / 8;
            for (int i = 0; i < frac; ++i) {
                v.push_back(N + 1 + i);
            }
            all_V[q] = v;
        }
        vector<int> observed_delta(17, 0);
        for (int q = 0; q < 17; ++q) {
            auto& v = all_V[q];
            int k = v.size() + 1;
            cout << "Query " << k << " " << a;
            for (int id : v) {
                cout << " " << id;
            }
            cout << endl;
            int res;
            cin >> res;
            int sz = v.size();
            observed_delta[q] = res - sz;
        }
        // non-mutual
        vector<tuple<int, int, int>> cand_non;
        for (int li = 0; li < N; ++li) {
            rec(0, 0, 0, li, cand_non, observed_delta, N);
        }
        vector<tuple<int, int, int>> filtered_non;
        for (auto [li, ri, ci] : cand_non) {
            bool match = true;
            for (int q = 9; q < 17; ++q) {
                auto& v = all_V[q];
                bool Lin = find(v.begin(), v.end(), N + 1 + li) != v.end();
                bool Rin = find(v.begin(), v.end(), N + 1 + ri) != v.end();
                bool Cin = find(v.begin(), v.end(), N + 1 + ci) != v.end();
                int exp = compute_delta(Lin, Rin, Cin);
                if (exp != observed_delta[q]) {
                    match = false;
                    break;
                }
            }
            if (match) {
                filtered_non.emplace_back(li, ri, ci);
            }
        }
        // mutual
        vector<int> cand_mut;
        int candidate_c = 0;
        bool cons = true;
        for (int bb = 0; bb < 9; ++bb) {
            int del = observed_delta[bb];
            int req_Cb;
            if (del == 1) req_Cb = 0;
            else if (del == 0) req_Cb = 1;
            else {
                cons = false;
                break;
            }
            if (req_Cb) candidate_c |= (1 << bb);
        }
        if (cons && candidate_c > 0 && candidate_c < N) {  // 0 to N-1
            bool match = true;
            for (int q = 9; q < 17; ++q) {
                auto& v = all_V[q];
                bool Cin = find(v.begin(), v.end(), N + 1 + candidate_c) != v.end();
                int exp_del = 1 - (Cin ? 1 : 0);
                if (exp_del != observed_delta[q]) {
                    match = false;
                    break;
                }
            }
            if (match) {
                cand_mut.push_back(candidate_c);
            }
        }
        int partner_index = -1;
        if (!filtered_non.empty()) {
            auto [l, r, c] = filtered_non[0];
            partner_index = c;
        } else if (!cand_mut.empty()) {
            partner_index = cand_mut[0];
        }
        // confirm
        if (partner_index != -1) {
            int bid = N + 1 + partner_index;
            cout << "Query 2 " << a << " " << bid << endl;
            int res;
            cin >> res;
            if (res == 1) {
                pairs[ai - 1] = {a, bid};
            }
        }
    }
    for (auto p : pairs) {
        cout << "Answer " << p.first << " " << p.second << endl;
    }
    return 0;
}