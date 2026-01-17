#include <bits/stdc++.h>
using namespace std;

static constexpr int S = 5; // 0=INIT, 1=(0,1),2=(0,2),3=(1,1),4=(1,2)

struct Choice {
    int worst = INT_MAX;
    int sum = INT_MAX;
    int balance = INT_MAX;
    int len = INT_MAX;
    int l = 1, r = 1;
    int insideSize = 0;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    int nextSt[S][2];
    // state 0 INIT
    nextSt[0][0] = 1; nextSt[0][1] = 3;
    // state 1: lastD=0, run=1
    nextSt[1][0] = 2; nextSt[1][1] = 3;
    // state 2: lastD=0, run=2
    nextSt[2][0] = -1; nextSt[2][1] = 3;
    // state 3: lastD=1, run=1
    nextSt[3][0] = 1; nextSt[3][1] = 4;
    // state 4: lastD=1, run=2
    nextSt[4][0] = 1; nextSt[4][1] = -1;

    auto surviveCount = [&](const array<int, S> &cnt, int A, int b) -> int {
        int D = A ^ b;
        int sum = 0;
        for (int s = 0; s < S; s++) if (nextSt[s][D] != -1) sum += cnt[s];
        return sum;
    };

    auto ask = [&](int l, int r) -> int {
        cout << "? " << l << " " << r << endl;
        int x;
        if (!(cin >> x)) exit(0);
        return (r - l + 1) - x; // b in {0,1}
    };

    auto mark = [&](int a) -> int {
        cout << "! " << a << endl;
        int y;
        if (!(cin >> y)) exit(0);
        return y;
    };

    for (int _case = 0; _case < t; _case++) {
        int n;
        cin >> n;

        int q0 = (int)ceil(log((double)n) / log(1.116));
        int limit = 2 * q0;

        vector<int> pos(n);
        vector<uint8_t> st(n, 0);
        for (int i = 0; i < n; i++) pos[i] = i + 1;

        int queries = 0;

        while ((int)pos.size() > 2 && queries < limit) {
            int m = (int)pos.size();

            vector<array<int, S>> pref(m + 1);
            pref[0].fill(0);
            for (int i = 0; i < m; i++) {
                pref[i + 1] = pref[i];
                pref[i + 1][st[i]]++;
            }
            array<int, S> total = pref[m];

            auto consider = [&](int l, int r, int insideSize, int surv0, int surv1, Choice &best) {
                int worst = max(surv0, surv1);
                int sum = surv0 + surv1;
                int balance = abs(insideSize - ((int)pos.size() - insideSize));
                int len = r - l + 1;

                if (worst < best.worst ||
                    (worst == best.worst && sum < best.sum) ||
                    (worst == best.worst && sum == best.sum && balance < best.balance) ||
                    (worst == best.worst && sum == best.sum && balance == best.balance && len < best.len)) {
                    best.worst = worst;
                    best.sum = sum;
                    best.balance = balance;
                    best.len = len;
                    best.l = l;
                    best.r = r;
                    best.insideSize = insideSize;
                }
            };

            Choice best;

            // Prefix queries: [1, mid]
            for (int k = 0; k <= m; k++) {
                int mid;
                if (k == 0) {
                    if (pos[0] == 1) continue;
                    mid = pos[0] - 1;
                } else if (k == m) {
                    mid = pos[m - 1];
                } else {
                    mid = pos[k] - 1;
                }
                if (mid < 1) continue;
                if (mid > n) mid = n;

                array<int, S> left = pref[k];
                array<int, S> right;
                for (int s = 0; s < S; s++) right[s] = total[s] - left[s];

                int surv0 = surviveCount(left, 1, 0) + surviveCount(right, 0, 0);
                int surv1 = surviveCount(left, 1, 1) + surviveCount(right, 0, 1);

                consider(1, mid, k, surv0, surv1, best);
            }

            // Suffix queries: [mid, n]
            for (int k = 0; k <= m; k++) {
                int mid;
                if (k == m) {
                    if (pos[m - 1] == n) continue;
                    mid = pos[m - 1] + 1;
                } else {
                    mid = pos[k];
                }
                if (mid < 1) mid = 1;
                if (mid > n) continue;

                array<int, S> left = pref[k];
                array<int, S> right;
                for (int s = 0; s < S; s++) right[s] = total[s] - left[s];

                int insideSize = m - k;

                int surv0 = surviveCount(left, 0, 0) + surviveCount(right, 1, 0);
                int surv1 = surviveCount(left, 0, 1) + surviveCount(right, 1, 1);

                consider(mid, n, insideSize, surv0, surv1, best);
            }

            // Ask chosen query
            int l = best.l, r = best.r;
            int b = ask(l, r);
            queries++;

            // Update candidates
            vector<int> npos;
            vector<uint8_t> nst;
            npos.reserve(pos.size());
            nst.reserve(pos.size());

            for (int i = 0; i < (int)pos.size(); i++) {
                int p = pos[i];
                int A = (l <= p && p <= r) ? 1 : 0;
                int D = A ^ b;
                int ns = nextSt[st[i]][D];
                if (ns != -1) {
                    npos.push_back(p);
                    nst.push_back((uint8_t)ns);
                }
            }

            pos.swap(npos);
            st.swap(nst);

            if (pos.empty()) {
                // Shouldn't happen; fall back to avoid infinite loop
                pos.push_back(1);
                st.push_back(0);
                break;
            }
        }

        // Finalize with up to 2 marks
        if (pos.empty()) {
            // Defensive
            pos.push_back(1);
        }

        int a1 = pos[0];
        int y1 = mark(a1);
        if (y1 == 0) {
            if ((int)pos.size() >= 2) {
                int a2 = pos[1];
                (void)mark(a2);
            } else {
                // No second candidate (should not happen); still allowed to mark someone
                int a2 = min(n, a1 == 1 ? 2 : 1);
                (void)mark(a2);
            }
        }

        cout << "#" << endl;
    }

    return 0;
}