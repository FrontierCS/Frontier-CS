#include <bits/stdc++.h>
using namespace std;

static int n;

static int ask(const vector<int>& pos) {
    cout << "? " << (int)pos.size();
    for (int x : pos) cout << ' ' << x;
    cout << '\n';
    cout.flush();
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

static int askAllExcept(const vector<int>& exc) {
    static vector<char> bad;
    bad.assign(n + 1, 0);
    for (int x : exc) if (1 <= x && x <= n) bad[x] = 1;
    vector<int> pos;
    pos.reserve(n - (int)exc.size());
    for (int i = 1; i <= n; i++) if (!bad[i]) pos.push_back(i);
    return ask(pos);
}

static long long lcmll(long long a, long long b) {
    return a / std::gcd(a, b) * b;
}

struct Anchor {
    int pos;
    int val;
};

static bool buildSubsets(const vector<Anchor>& anchors, const vector<int>& mods,
                         vector<vector<vector<int>>>& subsets) {
    subsets.clear();
    subsets.resize(mods.size());
    int A = (int)anchors.size();
    for (int mi = 0; mi < (int)mods.size(); mi++) {
        int mod = mods[mi];
        int s = mod - 1;
        if (A < s) return false;

        vector<vector<char>> dp(s + 1, vector<char>(mod, 0));
        vector<vector<int>> prevRes(s + 1, vector<int>(mod, -1));
        vector<vector<int>> prevIdx(s + 1, vector<int>(mod, -1));
        dp[0][0] = 1;

        for (int idx = 0; idx < A; idx++) {
            int add = anchors[idx].val % mod;
            for (int j = min(s, idx + 1); j >= 1; j--) {
                for (int r0 = 0; r0 < mod; r0++) if (dp[j - 1][r0]) {
                    int r = (r0 + add) % mod;
                    if (!dp[j][r]) {
                        dp[j][r] = 1;
                        prevRes[j][r] = r0;
                        prevIdx[j][r] = idx;
                    }
                }
            }
        }

        subsets[mi].assign(mod, {});
        for (int r = 0; r < mod; r++) {
            if (!dp[s][r]) return false;
            int cur = r, j = s;
            vector<int> chosenIdx;
            chosenIdx.reserve(s);
            while (j > 0) {
                int idx = prevIdx[j][cur];
                int pr = prevRes[j][cur];
                if (idx < 0 || pr < 0) return false;
                chosenIdx.push_back(idx);
                cur = pr;
                j--;
            }
            reverse(chosenIdx.begin(), chosenIdx.end());
            vector<int> pos;
            pos.reserve(s);
            for (int idx : chosenIdx) pos.push_back(anchors[idx].pos);
            subsets[mi][r] = std::move(pos);
        }
    }
    return true;
}

static bool addAnchor_n3_pair(vector<Anchor>& anchors, vector<int>& posToVal, vector<char>& hasVal,
                              long long totalSum) {
    if (n <= 8) return false;
    int m = n - 3;
    int A = (int)anchors.size();
    for (int ai = 0; ai < A; ai++) {
        for (int bi = ai + 1; bi < A; bi++) {
            int pa = anchors[ai].pos, pb = anchors[bi].pos;
            int va = anchors[ai].val, vb = anchors[bi].val;
            long long Rll = (totalSum - va - vb) % m;
            if (Rll < 0) Rll += m;
            int R = (int)Rll;

            if (R == 1 || R == 2 || R == 3) continue;
            int v = (R == 0 ? m : R);
            if (v <= 0 || v > n) continue;
            if (hasVal[v]) continue;
            if (v == va || v == vb) continue;

            int foundPos = -1;
            for (int i = 1; i <= n; i++) {
                if (i == pa || i == pb) continue;
                int ans = askAllExcept({pa, pb, i});
                if (ans == 1) {
                    if (foundPos != -1) { // unexpected ambiguity; abandon this candidate
                        foundPos = -2;
                        break;
                    }
                    foundPos = i;
                }
            }
            if (foundPos >= 1) {
                if (posToVal[foundPos] != -1) return false;
                posToVal[foundPos] = v;
                hasVal[v] = 1;
                anchors.push_back({foundPos, v});
                return true;
            }
        }
    }
    return false;
}

static void solveBruteforceSmall() {
    vector<vector<int>> queries;
    int N = n;
    int full = 1 << N;
    queries.reserve(full);
    for (int mask = 0; mask < full; mask++) {
        int cnt = __builtin_popcount((unsigned)mask);
        if (cnt >= 2 && cnt <= N - 1) {
            vector<int> pos;
            for (int b = 0; b < N; b++) if (mask & (1 << b)) pos.push_back(b + 1);
            queries.push_back(std::move(pos));
        }
    }

    vector<int> answers;
    answers.reserve(queries.size());
    for (auto &q : queries) answers.push_back(ask(q));

    vector<int> perm(N);
    iota(perm.begin(), perm.end(), 1);
    vector<int> best;
    do {
        if (perm[0] > N / 2) continue;
        bool ok = true;
        for (int qi = 0; qi < (int)queries.size(); qi++) {
            auto &q = queries[qi];
            long long sum = 0;
            for (int pos : q) sum += perm[pos - 1];
            int k = (int)q.size();
            int res = (sum % k == 0) ? 1 : 0;
            if (res != answers[qi]) { ok = false; break; }
        }
        if (ok) { best = perm; break; }
    } while (next_permutation(perm.begin(), perm.end()));

    if (best.empty()) best = vector<int>(N, 1);

    cout << "!";
    for (int i = 0; i < N; i++) cout << ' ' << best[i];
    cout << '\n';
    cout.flush();
    exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    if (n == 2) {
        cout << "! 1 2\n";
        cout.flush();
        return 0;
    }

    if (n <= 8) {
        solveBruteforceSmall();
        return 0;
    }

    long long totalSum = 1LL * n * (n + 1) / 2;

    // Choose moduli so that lcm(mods) > n
    vector<int> candidates = {3, 5, 7, 8};
    vector<int> mods;
    long long L = 1;
    for (int m : candidates) {
        if (m > n) continue;
        long long nL = lcmll(L, m);
        mods.push_back(m);
        L = nL;
        if (L > n) break;
    }
    // For safety (should not happen for n<=800 with candidates above)
    if (L <= n) {
        for (int m = 9; m <= n && L <= n; m++) {
            long long nL = lcmll(L, m);
            if (nL != L) {
                mods.push_back(m);
                L = nL;
            }
        }
    }

    vector<int> posToVal(n + 1, -1);
    vector<char> hasVal(n + 1, 0);
    vector<Anchor> anchors;

    // Find positions of {1, n} using k = n-1 queries (all except i)
    vector<int> extremePos;
    extremePos.reserve(2);
    for (int i = 1; i <= n; i++) {
        int ans = askAllExcept({i});
        if (ans == 1) extremePos.push_back(i);
    }
    // Arbitrarily label
    int posOne = extremePos.size() >= 1 ? extremePos[0] : 1;
    int posN = extremePos.size() >= 2 ? extremePos[1] : 2;

    posToVal[posOne] = 1; hasVal[1] = 1; anchors.push_back({posOne, 1});
    posToVal[posN] = n; hasVal[n] = 1; anchors.push_back({posN, n});

    // Find two more anchors via k = n-2 scans excluding posOne / posN
    {
        int m = n - 2;
        long long R1ll = (totalSum - 1) % m; if (R1ll < 0) R1ll += m;
        int v1 = (R1ll == 0 ? m : (int)R1ll);
        if (!hasVal[v1]) {
            int found = -1;
            for (int i = 1; i <= n; i++) {
                if (i == posOne) continue;
                int ans = askAllExcept({posOne, i});
                if (ans == 1) { found = i; break; }
            }
            if (found != -1) {
                posToVal[found] = v1; hasVal[v1] = 1; anchors.push_back({found, v1});
            }
        }
    }
    {
        int m = n - 2;
        long long R2ll = (totalSum - n) % m; if (R2ll < 0) R2ll += m;
        int v2 = (R2ll == 0 ? m : (int)R2ll);
        if (!hasVal[v2]) {
            int found = -1;
            for (int i = 1; i <= n; i++) {
                if (i == posN) continue;
                int ans = askAllExcept({posN, i});
                if (ans == 1) { found = i; break; }
            }
            if (found != -1) {
                posToVal[found] = v2; hasVal[v2] = 1; anchors.push_back({found, v2});
            }
        }
    }

    // Ensure anchor list has unique positions
    {
        sort(anchors.begin(), anchors.end(), [](const Anchor& a, const Anchor& b){return a.pos < b.pos;});
        anchors.erase(unique(anchors.begin(), anchors.end(),
                             [](const Anchor& a, const Anchor& b){return a.pos == b.pos;}), anchors.end());
    }

    vector<vector<vector<int>>> subsets;
    int maxAnchors = min(n, 28);
    while (true) {
        if (buildSubsets(anchors, mods, subsets)) break;
        if ((int)anchors.size() >= maxAnchors) break;
        if (!addAnchor_n3_pair(anchors, posToVal, hasVal, totalSum)) break;
    }
    // Final attempt
    if (!buildSubsets(anchors, mods, subsets)) {
        // Fallback: add anchors aggressively (best effort)
        while ((int)anchors.size() < maxAnchors && addAnchor_n3_pair(anchors, posToVal, hasVal, totalSum)) {
            if (buildSubsets(anchors, mods, subsets)) break;
        }
    }

    // Reconstruct permutation values
    vector<int> p(n + 1, -1);
    for (int i = 1; i <= n; i++) if (posToVal[i] != -1) p[i] = posToVal[i];

    for (int i = 1; i <= n; i++) {
        if (p[i] != -1) continue;

        vector<int> residues(mods.size(), -1);

        for (int mi = 0; mi < (int)mods.size(); mi++) {
            int mod = mods[mi];
            int found = -1;
            for (int r = 0; r <= mod - 2; r++) {
                int needSumResid = (mod - (r % mod)) % mod;
                const vector<int>& base = subsets[mi][needSumResid];
                vector<int> q;
                q.reserve(mod);
                for (int pos : base) q.push_back(pos);
                q.push_back(i);
                int ans = ask(q);
                if (ans == 1) { found = r; break; }
            }
            if (found == -1) found = mod - 1;
            residues[mi] = found;
        }

        int val = -1;
        for (int v = 1; v <= n; v++) {
            bool ok = true;
            for (int mi = 0; mi < (int)mods.size(); mi++) {
                if (v % mods[mi] != residues[mi]) { ok = false; break; }
            }
            if (ok) { val = v; break; }
        }
        if (val == -1) val = 1; // should not happen
        p[i] = val;
    }

    // Fix global complement if needed to satisfy p1 <= n/2
    if (p[1] > n / 2) {
        for (int i = 1; i <= n; i++) p[i] = n + 1 - p[i];
    }

    cout << "!";
    for (int i = 1; i <= n; i++) cout << ' ' << p[i];
    cout << '\n';
    cout.flush();
    return 0;
}