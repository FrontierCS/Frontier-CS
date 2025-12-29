#include <bits/stdc++.h>
using namespace std;

const int MAXN = 100;

struct XorShift {
    unsigned long long x;
    XorShift(unsigned long long seed = 88172645463325252ULL) { x = seed; }
    unsigned long long next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    int nextInt(int n) {
        return (int)(next() % n);
    }
};

long long simulate(const int a[], const int b[], int N, int L, const vector<int>& T) {
    static int cnt[MAXN];
    fill(cnt, cnt + N, 0);
    int cur = 0;
    for (int w = 1; w <= L; ++w) {
        cnt[cur]++;
        if (w == L) break;
        if (cnt[cur] & 1) cur = a[cur];
        else cur = b[cur];
    }
    long long err = 0;
    for (int i = 0; i < N; ++i) {
        err += llabs((long long)cnt[i] - (long long)T[i]);
    }
    return err;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, L;
    if (!(cin >> N >> L)) return 0;
    vector<int> T(N);
    for (int i = 0; i < N; ++i) cin >> T[i];

    int a[MAXN], b[MAXN];
    vector<int> cntInit(N, 0);
    fill(a, a + N, -1);
    fill(b, b + N, -1);

    // Initial greedy construction
    int cur = 0;
    for (int week = 1; week <= L; ++week) {
        int x = cur;
        cntInit[x]++;
        if (week == L) break;
        int parity = cntInit[x] & 1; // 1: odd -> use a[x], 0: even -> use b[x]
        int &edge = (parity ? a[x] : b[x]);
        if (edge == -1) {
            long long bestDiff = LLONG_MIN;
            int bestJ = 0;
            for (int j = 0; j < N; ++j) {
                long long diff = (long long)T[j] - (long long)cntInit[j];
                if (diff > bestDiff) {
                    bestDiff = diff;
                    bestJ = j;
                }
            }
            edge = bestJ;
        }
        cur = edge;
    }

    // Fill unused edges with 0 (will be adjusted by local search if needed)
    for (int i = 0; i < N; ++i) {
        if (a[i] == -1) a[i] = 0;
        if (b[i] == -1) b[i] = 0;
    }

    long long best_err = 0;
    for (int i = 0; i < N; ++i) {
        best_err += llabs((long long)cntInit[i] - (long long)T[i]);
    }

    // Local search (hill climbing) with time limit
    unsigned long long seed =
        (unsigned long long)chrono::steady_clock::now().time_since_epoch().count();
    XorShift rng(seed);

    auto start_time = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.8; // seconds

    int iterations = 0;
    while (true) {
        ++iterations;
        if ((iterations & 127) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > TIME_LIMIT) break;
        }

        int i = rng.nextInt(N);
        bool chooseA = (rng.next() & 1ULL);
        int &edge = chooseA ? a[i] : b[i];
        int oldTo = edge;
        if (N > 1) {
            int newTo;
            do {
                newTo = rng.nextInt(N);
            } while (newTo == oldTo);
            edge = newTo;
        } else {
            continue;
        }

        long long err = simulate(a, b, N, L, T);
        if (err < best_err) {
            best_err = err;
        } else {
            edge = oldTo;
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << a[i] << ' ' << b[i] << '\n';
    }

    return 0;
}