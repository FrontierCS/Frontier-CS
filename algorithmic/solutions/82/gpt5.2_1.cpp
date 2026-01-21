#include <bits/stdc++.h>
using namespace std;

static constexpr int QUERY_LIMIT = 4269;

struct Interactor {
    long long used = 0;

    int ask(int i, int j) {
        cout << "? " << i << " " << j << "\n";
        cout.flush();
        int x;
        if (!(cin >> x)) exit(0);
        if (x == -1) exit(0);
        ++used;
        return x;
    }

    void answer(const vector<int>& p) {
        cout << "!";
        for (int i = 1; i < (int)p.size(); i++) cout << " " << p[i];
        cout << "\n";
        cout.flush();
    }
};

static inline long long choose2(long long m) { return m * (m - 1) / 2; }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    Interactor it;

    const int MAXMASK = (1 << 11) - 1; // up to 2047

    // Deterministic for small n: query all pairs, compute p_i = AND_{j!=i} (p_i | p_j)
    if (n <= 92) {
        vector<int> p(n + 1, MAXMASK);
        for (int i = 1; i <= n; i++) {
            for (int j = i + 1; j <= n; j++) {
                int v = it.ask(i, j);
                p[i] &= v;
                p[j] &= v;
            }
        }
        it.answer(p);
        return 0;
    }

    // Large n: find two indices a,b with p_a & p_b == 0 using limited random sampling,
    // then recover all other values via (p_i|p_a)&(p_i|p_b) = p_i.
    long long finalQueriesNeeded = 2LL * (n - 2);
    long long searchBudget = QUERY_LIMIT - finalQueriesNeeded;
    if (searchBudget < 0) searchBudget = 0;

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    auto run_attempt = [&](int m) -> optional<pair<int,int>> {
        if (m < 2) return nullopt;
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 1);
        shuffle(idx.begin(), idx.end(), rng);
        idx.resize(m);

        vector<int> A(m, MAXMASK);
        for (int i = 0; i < m; i++) {
            for (int j = i + 1; j < m; j++) {
                int v = it.ask(idx[i], idx[j]);
                A[i] &= v;
                A[j] &= v;
            }
        }

        for (int i = 0; i < m; i++) {
            for (int j = i + 1; j < m; j++) {
                if ( (A[i] & A[j]) == 0 ) return pair<int,int>(idx[i], idx[j]);
            }
        }
        return nullopt;
    };

    vector<int> attemptSizes;
    // Reserve a tiny margin
    long long budget = max(0LL, searchBudget - 2);

    auto addAttempt = [&](int m) {
        m = min(m, n);
        if (m < 2) return;
        long long c = choose2(m);
        if (c <= budget) {
            attemptSizes.push_back(m);
            budget -= c;
        }
    };

    // Prefer multiple attempts over one large attempt when budget is tight.
    if (searchBudget >= 175) {
        addAttempt(16);
        addAttempt(11);
    } else if (searchBudget >= 150) {
        addAttempt(15);
        addAttempt(10);
    } else if (searchBudget >= 127) {
        addAttempt(14);
        addAttempt(9);
    } else {
        // One best-effort attempt
        long long b = budget;
        int m = (int)floor((1.0 + sqrt(1.0 + 8.0 * (double)b)) / 2.0);
        addAttempt(m);
    }

    // If we still have budget, add a couple more smaller attempts.
    for (int m : {22, 20, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8}) {
        if ((int)attemptSizes.size() >= 6) break;
        addAttempt(m);
    }

    optional<pair<int,int>> bases;
    for (int m : attemptSizes) {
        bases = run_attempt(m);
        if (bases) break;
    }

    // Very unlikely fallback: try a couple tiny attempts if any budget remains.
    if (!bases) {
        for (int m : {12, 11, 10, 9, 8, 7, 6}) {
            long long c = choose2(min(m, n));
            if (it.used + c + finalQueriesNeeded <= QUERY_LIMIT) {
                bases = run_attempt(min(m, n));
                if (bases) break;
            }
        }
    }

    if (!bases) {
        // Last resort (should not happen with high probability): pick 1 and 2.
        bases = {1, 2};
    }

    int a = bases->first;
    int b = bases->second;
    if (a == b) {
        b = (a % n) + 1;
    }

    vector<int> orA(n + 1, -1), orB(n + 1, -1);
    vector<int> p(n + 1, -1);

    for (int i = 1; i <= n; i++) {
        if (i == a || i == b) continue;
        orA[i] = it.ask(a, i);
        orB[i] = it.ask(b, i);
        p[i] = (orA[i] & orB[i]);
    }

    vector<char> usedVal(n, 0);
    for (int i = 1; i <= n; i++) {
        if (i == a || i == b) continue;
        if (p[i] >= 0 && p[i] < n) usedVal[p[i]] = 1;
    }
    vector<int> missing;
    for (int v = 0; v < n; v++) if (!usedVal[v]) missing.push_back(v);

    auto checkAssign = [&](int va, int vb) -> bool {
        for (int i = 1; i <= n; i++) {
            if (i == a || i == b) continue;
            if ( (p[i] | va) != orA[i] ) return false;
            if ( (p[i] | vb) != orB[i] ) return false;
        }
        return true;
    };

    if ((int)missing.size() == 2) {
        int u = missing[0], v = missing[1];
        if (checkAssign(u, v)) {
            p[a] = u; p[b] = v;
        } else {
            p[a] = v; p[b] = u;
        }
    } else {
        // Should not happen; fill defensively.
        vector<int> all(n);
        iota(all.begin(), all.end(), 0);
        vector<char> seen(n, 0);
        for (int i = 1; i <= n; i++) if (i != a && i != b && p[i] >= 0 && p[i] < n) seen[p[i]] = 1;
        int u = -1, v = -1;
        for (int x = 0; x < n; x++) if (!seen[x]) { if (u == -1) u = x; else v = x; }
        if (u == -1) u = 0;
        if (v == -1) v = (u == 0 ? 1 : 0);
        p[a] = u; p[b] = v;
    }

    it.answer(p);
    return 0;
}