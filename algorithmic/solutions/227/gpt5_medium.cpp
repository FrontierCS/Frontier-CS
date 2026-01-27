#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n;
    vector<int> p;
    vector<char> mark;

    vector<int> extractLIS(const vector<int>& seq, int mode) {
        int m = (int)seq.size();
        if (m == 0) return {};
        vector<int> prev(m, -1);
        vector<int> tailVal;
        vector<int> tailPos;
        tailVal.reserve(m);
        tailPos.reserve(m);

        for (int pos = 0; pos < m; ++pos) {
            int val = p[seq[pos]];
            if (mode == -1) val = -val;
            int idx = lower_bound(tailVal.begin(), tailVal.end(), val) - tailVal.begin();
            int prevPos = (idx > 0 ? tailPos[idx - 1] : -1);
            if (idx == (int)tailVal.size()) {
                tailVal.push_back(val);
                tailPos.push_back(pos);
            } else {
                tailVal[idx] = val;
                tailPos[idx] = pos;
            }
            prev[pos] = prevPos;
        }
        int len = (int)tailVal.size();
        int pos = tailPos[len - 1];
        vector<int> res;
        while (pos != -1) {
            res.push_back(seq[pos]);
            pos = prev[pos];
        }
        reverse(res.begin(), res.end());
        return res;
    }

    int LISLen(const vector<int>& seq, int mode) {
        vector<int> tails;
        tails.reserve(seq.size());
        for (int idx : seq) {
            int val = p[idx];
            if (mode == -1) val = -val;
            int it = lower_bound(tails.begin(), tails.end(), val) - tails.begin();
            if (it == (int)tails.size()) tails.push_back(val);
            else tails[it] = val;
        }
        return (int)tails.size();
    }

    vector<int> set_diff(const vector<int>& seq, const vector<int>& selected) {
        for (int idx : selected) mark[idx] = 1;
        vector<int> res;
        res.reserve(seq.size() - selected.size());
        for (int idx : seq) if (!mark[idx]) res.push_back(idx);
        for (int idx : selected) mark[idx] = 0;
        return res;
    }

    void finalizeCandidate(const vector<int>& A, const vector<int>& B, const vector<int>& C, const vector<int>& D,
                           int &bestScore, vector<int>& bestA, vector<int>& bestB, vector<int>& bestC, vector<int>& bestD) {
        int score = 0;
        score += LISLen(A, +1);
        score += LISLen(B, -1);
        score += LISLen(C, +1);
        score += LISLen(D, -1);
        if (score > bestScore) {
            bestScore = score;
            bestA = A; bestB = B; bestC = C; bestD = D;
        }
    }

    void solve() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        cin >> n;
        p.resize(n);
        for (int i = 0; i < n; ++i) cin >> p[i];
        mark.assign(n, 0);

        vector<int> base(n);
        iota(base.begin(), base.end(), 0);

        int bestScore = -1;
        vector<int> bestA, bestB, bestC, bestD;

        // Scenario family S1: A (LIS) then B (LDS), then tail options
        {
            vector<int> A = extractLIS(base, +1);
            vector<int> rem1 = set_diff(base, A);

            vector<int> B = extractLIS(rem1, -1);
            vector<int> rem2 = set_diff(rem1, B);

            // Option1: C = LIS(rem2), D = rem2 \ C
            {
                vector<int> C = extractLIS(rem2, +1);
                vector<int> D = set_diff(rem2, C);
                finalizeCandidate(A, B, C, D, bestScore, bestA, bestB, bestC, bestD);
            }
            // Option2: C = empty, D = rem2
            {
                vector<int> C;
                vector<int> D = rem2;
                finalizeCandidate(A, B, C, D, bestScore, bestA, bestB, bestC, bestD);
            }
            // Option3: D = LDS(rem2), C = rem2 \ D
            {
                vector<int> D = extractLIS(rem2, -1);
                vector<int> C = set_diff(rem2, D);
                finalizeCandidate(A, B, C, D, bestScore, bestA, bestB, bestC, bestD);
            }
        }

        // Scenario family S2: B (LDS) then A (LIS), then tail options
        {
            vector<int> B = extractLIS(base, -1);
            vector<int> rem1 = set_diff(base, B);

            vector<int> A = extractLIS(rem1, +1);
            vector<int> rem2 = set_diff(rem1, A);

            // Option1: C = LIS(rem2), D = rem2 \ C
            {
                vector<int> C = extractLIS(rem2, +1);
                vector<int> D = set_diff(rem2, C);
                finalizeCandidate(A, B, C, D, bestScore, bestA, bestB, bestC, bestD);
            }
            // Option2: C = empty, D = rem2
            {
                vector<int> C;
                vector<int> D = rem2;
                finalizeCandidate(A, B, C, D, bestScore, bestA, bestB, bestC, bestD);
            }
            // Option3: D = LDS(rem2), C = rem2 \ D
            {
                vector<int> D = extractLIS(rem2, -1);
                vector<int> C = set_diff(rem2, D);
                finalizeCandidate(A, B, C, D, bestScore, bestA, bestB, bestC, bestD);
            }
        }

        // Scenario S3: A only, then split remain into C and D; B empty
        {
            vector<int> A = extractLIS(base, +1);
            vector<int> rem1 = set_diff(base, A);

            // Option1
            {
                vector<int> C = extractLIS(rem1, +1);
                vector<int> D = set_diff(rem1, C);
                vector<int> B;
                finalizeCandidate(A, B, C, D, bestScore, bestA, bestB, bestC, bestD);
            }
            // Option2
            {
                vector<int> C;
                vector<int> D = rem1;
                vector<int> B;
                finalizeCandidate(A, B, C, D, bestScore, bestA, bestB, bestC, bestD);
            }
            // Option3
            {
                vector<int> D = extractLIS(rem1, -1);
                vector<int> C = set_diff(rem1, D);
                vector<int> B;
                finalizeCandidate(A, B, C, D, bestScore, bestA, bestB, bestC, bestD);
            }
        }

        // Scenario S4: B only, then split remain into C and D; A empty
        {
            vector<int> B = extractLIS(base, -1);
            vector<int> rem1 = set_diff(base, B);

            // Option1
            {
                vector<int> C = extractLIS(rem1, +1);
                vector<int> D = set_diff(rem1, C);
                vector<int> A;
                finalizeCandidate(A, B, C, D, bestScore, bestA, bestB, bestC, bestD);
            }
            // Option2
            {
                vector<int> C;
                vector<int> D = rem1;
                vector<int> A;
                finalizeCandidate(A, B, C, D, bestScore, bestA, bestB, bestC, bestD);
            }
            // Option3
            {
                vector<int> D = extractLIS(rem1, -1);
                vector<int> C = set_diff(rem1, D);
                vector<int> A;
                finalizeCandidate(A, B, C, D, bestScore, bestA, bestB, bestC, bestD);
            }
        }

        // Scenario S5: none first; split base into C and D; A and B empty
        {
            vector<int> A, B;

            // Option1
            {
                vector<int> C = extractLIS(base, +1);
                vector<int> D = set_diff(base, C);
                finalizeCandidate(A, B, C, D, bestScore, bestA, bestB, bestC, bestD);
            }
            // Option2
            {
                vector<int> C;
                vector<int> D = base;
                finalizeCandidate(A, B, C, D, bestScore, bestA, bestB, bestC, bestD);
            }
            // Option3
            {
                vector<int> D = extractLIS(base, -1);
                vector<int> C = set_diff(base, D);
                finalizeCandidate(A, B, C, D, bestScore, bestA, bestB, bestC, bestD);
            }
        }

        // Ensure partition covers all elements; if not, assign leftovers to d
        // (Should already be covered by construction, but safe-check)
        {
            vector<char> seen(n, 0);
            for (int x : bestA) seen[x] = 1;
            for (int x : bestB) seen[x] = 1;
            for (int x : bestC) seen[x] = 1;
            for (int x : bestD) seen[x] = 1;
            vector<int> leftover;
            leftover.reserve(n);
            for (int i = 0; i < n; ++i) if (!seen[i]) leftover.push_back(i);
            if (!leftover.empty()) {
                // Append to D to keep partition complete
                for (int x : leftover) bestD.push_back(x);
            }
        }

        int ra = (int)bestA.size();
        int sb = (int)bestB.size();
        int pc = (int)bestC.size();
        int qd = (int)bestD.size();

        cout << ra << " " << sb << " " << pc << " " << qd << "\n";
        for (int i = 0; i < ra; ++i) {
            if (i) cout << " ";
            cout << p[bestA[i]];
        }
        cout << "\n";
        for (int i = 0; i < sb; ++i) {
            if (i) cout << " ";
            cout << p[bestB[i]];
        }
        cout << "\n";
        for (int i = 0; i < pc; ++i) {
            if (i) cout << " ";
            cout << p[bestC[i]];
        }
        cout << "\n";
        for (int i = 0; i < qd; ++i) {
            if (i) cout << " ";
            cout << p[bestD[i]];
        }
        cout << "\n";
    }
};

int main() {
    Solver s;
    s.solve();
    return 0;
}