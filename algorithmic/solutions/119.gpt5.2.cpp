#include <bits/stdc++.h>
using namespace std;

static const long long MOD = 1000000007LL;

static long long modSub(long long a, long long b) {
    a -= b;
    if (a < 0) a += MOD;
    return a;
}

struct Solver {
    int n;
    int qcnt = 0;

    long long ask(const vector<long long>& a) {
        cout << "?";
        for (int i = 0; i <= n; i++) cout << ' ' << a[i];
        cout << '\n' << flush;

        long long r;
        if (!(cin >> r)) exit(0);
        if (r < 0) exit(0);
        qcnt++;
        return r;
    }

    optional<vector<int>> attemptPlusFirst(int K, const vector<long long>& diff) {
        vector<int> ops(n, 0); // 0:+, 1:*
        ops[0] = 0;
        int cntPlus = 1;
        long long p = 1; // plus count among op[1..i-1] before current i
        for (int i = 2; i <= n; i++) {
            if (diff[i] == 1) {
                ops[i - 1] = 0;
                cntPlus++;
                p++;
            } else {
                ops[i - 1] = 1;
                if (diff[i] != 1 + p) return nullopt;
            }
        }
        if (cntPlus != K) return nullopt;
        return ops;
    }

    optional<vector<int>> attemptMulFirst(int K, const vector<long long>& diff) {
        vector<int> ops(n, 1); // default '*'
        ops[0] = 1;
        int cntPlus = 0;

        bool allOnes = true;
        for (int i = 2; i <= n; i++) {
            if (diff[i] != 1) { allOnes = false; break; }
        }

        if (allOnes) {
            int prefixMul = n - K;
            if (prefixMul < 1 || prefixMul > n) return nullopt;
            for (int pos = 1; pos <= prefixMul; pos++) ops[pos - 1] = 1;
            for (int pos = prefixMul + 1; pos <= n; pos++) ops[pos - 1] = 0;
            cntPlus = n - prefixMul;
            if (cntPlus != K) return nullopt;
            return ops;
        }

        int m = -1;
        for (int i = 2; i <= n; i++) {
            if (diff[i] > 1) { m = i; break; }
        }
        if (m == -1) return nullopt;

        long long p_m = diff[m] - 1; // >=1
        long long L = (m - 1) - p_m; // number of initial multiplications (>=1)
        if (L < 1 || L >= m) return nullopt;

        for (int pos = 1; pos <= (int)L; pos++) ops[pos - 1] = 1;
        for (int pos = (int)L + 1; pos <= m - 1; pos++) ops[pos - 1] = 0;
        ops[m - 1] = 1;

        cntPlus = (int)p_m;
        long long p = p_m; // plus count before positions > m

        for (int i = m + 1; i <= n; i++) {
            if (diff[i] == 1) {
                ops[i - 1] = 0;
                cntPlus++;
                p++;
            } else {
                ops[i - 1] = 1;
                if (diff[i] != 1 + p) return nullopt;
            }
        }

        if (cntPlus != K) return nullopt;
        return ops;
    }

    void run() {
        cin >> n;
        vector<long long> a(n + 1, 1);

        long long base = ask(a);
        int K = (int)((base + MOD - 1) % MOD);

        if (K == 0) {
            cout << "!";
            for (int i = 0; i < n; i++) cout << " 1";
            cout << '\n' << flush;
            return;
        }
        if (K == n) {
            cout << "!";
            for (int i = 0; i < n; i++) cout << " 0";
            cout << '\n' << flush;
            return;
        }
        if (n == 1) {
            cout << "! " << (K == 1 ? 0 : 1) << '\n' << flush;
            return;
        }

        vector<long long> diff(n + 1, 0);
        for (int i = 2; i <= n; i++) {
            a[i] = 2;
            long long r = ask(a);
            a[i] = 1;
            diff[i] = modSub(r, base);
        }

        auto candPlus = attemptPlusFirst(K, diff);
        auto candMul = attemptMulFirst(K, diff);

        vector<int> ans;
        if (candPlus && !candMul) ans = *candPlus;
        else if (!candPlus && candMul) ans = *candMul;
        else if (candPlus && candMul) {
            if (*candPlus == *candMul) ans = *candPlus;
            else ans = *candPlus; // should not happen
        } else {
            ans.assign(n, 1); // fallback
        }

        cout << "!";
        for (int i = 0; i < n; i++) cout << ' ' << ans[i];
        cout << '\n' << flush;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Solver s;
    s.run();
    return 0;
}