#include <bits/stdc++.h>
using namespace std;

static inline int letter_idx(char ch) {
    switch (ch) {
        case 'A': return 0;
        case 'C': return 1;
        case 'G': return 2;
        case 'T': return 3;
        default: return -1;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> s(m);
    for (int i = 0; i < m; ++i) cin >> s[i];

    // Remove dominated patterns: if pattern i is a superset of j, drop j
    vector<char> alive(m, 1);
    for (int i = 0; i < m; ++i) {
        if (!alive[i]) continue;
        for (int j = 0; j < m; ++j) {
            if (i == j || !alive[j]) continue;
            bool sup = true;
            for (int p = 0; p < n; ++p) {
                char a = s[i][p], b = s[j][p];
                if (a != '?' && a != b) { sup = false; break; }
            }
            if (sup) alive[j] = 0;
        }
    }
    vector<string> pat;
    pat.reserve(m);
    for (int i = 0; i < m; ++i) if (alive[i]) pat.push_back(s[i]);
    s.swap(pat);
    m = (int)s.size();

    if (m == 0) {
        cout.setf(std::ios::fixed); cout << setprecision(15) << 0.0 << "\n";
        return 0;
    }

    // If any pattern is all '?', coverage is 1
    for (int i = 0; i < m; ++i) {
        bool allq = true;
        for (int p = 0; p < n; ++p) {
            if (s[i][p] != '?') { allq = false; break; }
        }
        if (allq) {
            cout.setf(std::ios::fixed); cout << setprecision(15) << 1.0 << "\n";
            return 0;
        }
    }

    using Mask = uint64_t;
    Mask full_mask = (m == 64) ? ~0ull : ((1ull << m) - 1ull);

    // Precompute steps: for each position, store unique (mask, weight) pairs
    struct Step { vector<pair<Mask, double>> trans; };
    vector<Step> steps;
    steps.reserve(n);
    for (int j = 0; j < n; ++j) {
        array<Mask, 4> M = {0,0,0,0};
        for (int i = 0; i < m; ++i) {
            char c = s[i][j];
            if (c == '?') {
                M[0] |= (Mask(1) << i);
                M[1] |= (Mask(1) << i);
                M[2] |= (Mask(1) << i);
                M[3] |= (Mask(1) << i);
            } else {
                int k = letter_idx(c);
                if (k >= 0) M[k] |= (Mask(1) << i);
            }
        }
        // If all masks are full_mask (all '?'), skip this position
        if (M[0] == full_mask && M[1] == full_mask && M[2] == full_mask && M[3] == full_mask) continue;

        // Compress identical masks among 4 letters: accumulate counts
        vector<pair<Mask, int>> uniq;
        for (int c = 0; c < 4; ++c) {
            Mask mm = M[c];
            bool found = false;
            for (auto &pr : uniq) {
                if (pr.first == mm) { pr.second += 1; found = true; break; }
            }
            if (!found) uniq.emplace_back(mm, 1);
        }
        Step st;
        st.trans.reserve(uniq.size());
        for (auto &pr : uniq) {
            st.trans.emplace_back(pr.first, pr.second / 4.0);
        }
        steps.push_back(move(st));
    }

    // If no effective steps (all positions were all '?'), probability is 1
    if (steps.empty()) {
        cout.setf(std::ios::fixed); cout << setprecision(15) << 1.0 << "\n";
        return 0;
    }

    // Choose method based on m
    const int ARRAY_DP_THRESHOLD = 22; // safe threshold for array DP
    double result = 0.0;

    if (m <= ARRAY_DP_THRESHOLD) {
        size_t TOT = 1ull << m;
        vector<double> dp(TOT, 0.0), dp2(TOT, 0.0);
        dp[TOT - 1] = 1.0;
        for (const auto &st : steps) {
            fill(dp2.begin(), dp2.end(), 0.0);
            const auto &trs = st.trans;
            for (size_t S = 0; S < TOT; ++S) {
                double val = dp[S];
                if (val == 0.0) continue;
                for (const auto &pr : trs) {
                    Mask mm = pr.first;
                    double w = pr.second;
                    size_t S2 = S & (size_t)mm;
                    dp2[S2] += val * w;
                }
            }
            dp.swap(dp2);
        }
        double p_invalid = dp[0];
        double p_valid = 1.0 - p_invalid;
        if (p_valid < 0) p_valid = 0;
        if (p_valid > 1) p_valid = 1;
        result = p_valid;
    } else {
        // Map-based DP for larger m
        vector<pair<Mask, double>> cur, nxt;
        cur.emplace_back(full_mask, 1.0);
        for (const auto &st : steps) {
            const auto &trs = st.trans;
            nxt.clear();
            nxt.reserve(cur.size() * trs.size());
            for (const auto &pr : cur) {
                Mask cmask = pr.first;
                double p = pr.second;
                for (const auto &tr : trs) {
                    Mask nm = cmask & tr.first;
                    double add = p * tr.second;
                    nxt.emplace_back(nm, add);
                }
            }
            // Combine duplicates by sorting
            sort(nxt.begin(), nxt.end(), [](const pair<Mask,double>& a, const pair<Mask,double>& b){
                return a.first < b.first;
            });
            cur.clear();
            cur.reserve(nxt.size());
            for (size_t i = 0; i < nxt.size(); ) {
                Mask mk = nxt[i].first;
                double sum = 0.0;
                size_t j = i;
                while (j < nxt.size() && nxt[j].first == mk) {
                    sum += nxt[j].second;
                    ++j;
                }
                cur.emplace_back(mk, sum);
                i = j;
            }
        }
        double p_invalid = 0.0;
        for (auto &pr : cur) {
            if (pr.first == 0) { p_invalid = pr.second; break; }
        }
        double p_valid = 1.0 - p_invalid;
        if (p_valid < 0) p_valid = 0;
        if (p_valid > 1) p_valid = 1;
        result = p_valid;
    }

    cout.setf(std::ios::fixed);
    cout << setprecision(15) << result << "\n";
    return 0;
}