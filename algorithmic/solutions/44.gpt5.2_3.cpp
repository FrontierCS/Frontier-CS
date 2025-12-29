#include <bits/stdc++.h>
using namespace std;

static inline long double dist2d(const vector<long long>& xs, const vector<long long>& ys, int a, int b) {
    long double dx = (long double)xs[a] - (long double)xs[b];
    long double dy = (long double)ys[a] - (long double)ys[b];
    return sqrtl(dx * dx + dy * dy);
}

struct Solver {
    int N;
    vector<long long> xs, ys;
    vector<char> isPrime;
    vector<int> P;
    vector<char> locked;
    set<int> primePos;

    int cityBefore(int pos) const {
        if (pos == N) return 0;
        return P[pos];
    }

    int cityAfter(int pos, int a, int b) const {
        if (pos == N) return 0;
        if (pos == a) return P[b];
        if (pos == b) return P[a];
        return P[pos];
    }

    long double swapDelta(int a, int b) const {
        if (a == b) return 0;
        if (a > b) swap(a, b);

        int edgesArr[4] = {a - 1, a, b - 1, b};
        vector<int> edges;
        edges.reserve(4);
        for (int e : edgesArr) {
            if (0 <= e && e < N) edges.push_back(e);
        }
        sort(edges.begin(), edges.end());
        edges.erase(unique(edges.begin(), edges.end()), edges.end());

        long double before = 0, after = 0;
        for (int e : edges) {
            int u = cityBefore(e);
            int v = cityBefore(e + 1);
            before += dist2d(xs, ys, u, v);

            int u2 = cityAfter(e, a, b);
            int v2 = cityAfter(e + 1, a, b);
            after += dist2d(xs, ys, u2, v2);
        }
        return after - before;
    }

    void updatePos(int idx) {
        if (idx <= 0 || idx >= N) return;
        if (locked[idx]) {
            primePos.erase(idx);
            return;
        }
        if (isPrime[P[idx]]) primePos.insert(idx);
        else primePos.erase(idx);
    }

    void initPrimes() {
        isPrime.assign(N, true);
        if (N > 0) isPrime[0] = false;
        if (N > 1) isPrime[1] = false;
        for (int p = 2; (long long)p * p < N; ++p) {
            if (!isPrime[p]) continue;
            for (int j = p * p; j < N; j += p) isPrime[j] = false;
        }
    }

    void buildInitialTourZigzag() {
        P.assign(N, 0);
        P[0] = 0;
        int idx = 1;
        for (int i = 1; i < N; i += 2) P[idx++] = i;
        int startEven = ((N - 1) % 2 == 0) ? (N - 1) : (N - 2);
        for (int i = startEven; i >= 2; i -= 2) P[idx++] = i;
        // idx should be N
    }

    int chooseDonor(int pos, int MAX_DIST, int K_NEI) const {
        // Only use donors from positions that are NOT penalty-source positions (pos%10 != 9)
        auto it0 = primePos.lower_bound(pos);
        vector<int> cand;
        cand.reserve(2 * K_NEI);

        auto it = it0;
        for (int k = 0; k < K_NEI && it != primePos.end(); ++k, ++it) {
            int q = *it;
            int d = q - pos;
            if (d > MAX_DIST) break;
            if (q % 10 == 9) continue;
            cand.push_back(q);
        }

        it = it0;
        for (int k = 0; k < K_NEI && it != primePos.begin(); ++k) {
            --it;
            int q = *it;
            int d = pos - q;
            if (d > MAX_DIST) break;
            if (q % 10 == 9) continue;
            cand.push_back(q);
        }

        if (cand.empty()) return -1;

        int bestQ = -1;
        long double bestDelta = 0;
        int bestAbs = INT_MAX;

        for (int q : cand) {
            int absd = abs(q - pos);
            long double delta = swapDelta(pos, q);
            if (bestQ == -1 || delta < bestDelta - 1e-18L || (fabsl(delta - bestDelta) <= 1e-18L && absd < bestAbs)) {
                bestQ = q;
                bestDelta = delta;
                bestAbs = absd;
            }
        }
        return bestQ;
    }

    void run() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        cin >> N;
        xs.resize(N);
        ys.resize(N);
        for (int i = 0; i < N; i++) {
            cin >> xs[i] >> ys[i];
        }

        initPrimes();
        buildInitialTourZigzag();

        locked.assign(N, false);
        locked[0] = true;

        primePos.clear();
        for (int i = 1; i < N; i++) {
            if (!locked[i] && isPrime[P[i]]) primePos.insert(i);
        }

        const int MAX_DIST = 200;
        const int K_NEI = 6;

        for (int pos = 9; pos <= N - 1; pos += 10) {
            if (locked[pos]) continue;

            if (isPrime[P[pos]]) {
                locked[pos] = true;
                updatePos(pos);
                continue;
            }

            int q = chooseDonor(pos, MAX_DIST, K_NEI);
            if (q == -1) continue;

            swap(P[pos], P[q]);
            locked[pos] = true;
            updatePos(pos);
            updatePos(q);
        }

        cout << (N + 1) << '\n';
        for (int i = 0; i < N; i++) cout << P[i] << '\n';
        cout << 0 << '\n';
    }
};

int main() {
    Solver s;
    s.run();
    return 0;
}