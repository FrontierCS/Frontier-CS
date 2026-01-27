#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];
    inline int read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return EOF;
        }
        return buf[idx++];
    }
    inline bool skipBlanks() {
        int c;
        do {
            c = read();
            if (c == EOF) return false;
        } while (c <= ' ');
        idx--;
        return true;
    }
    inline int nextInt() {
        if (!skipBlanks()) return 0;
        int c = read();
        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = read();
        }
        return x;
    }
};

static inline int compute_cost(const vector<int>& p, const vector<uint8_t>& D, const vector<uint8_t>& F, int n) {
    const uint8_t* d = D.data();
    const uint8_t* f = F.data();
    long long cost = 0;
    for (int i = 0; i < n; ++i) {
        int pi = p[i] * n;
        const uint8_t* fi = f + i * n;
        for (int j = 0; j < n; ++j) {
            if (fi[j]) {
                cost += d[pi + p[j]];
            }
        }
    }
    return (int)cost;
}

static inline int delta_swap(int a, int b, const vector<int>& p, const vector<uint8_t>& D, const vector<uint8_t>& F, int n) {
    int la = p[a], lb = p[b];
    if (la == lb) return 0;
    const uint8_t* d = D.data();
    const uint8_t* f = F.data();
    int delta = 0;
    int la_n = la * n, lb_n = lb * n;

    for (int k = 0; k < n; ++k) {
        if (k == a || k == b) continue;
        int pk = p[k];
        int pk_n = pk * n;
        // (a,k) and (k,a)
        delta += (int)f[a * n + k] * ((int)d[lb_n + pk] - (int)d[la_n + pk]);
        delta += (int)f[k * n + a] * ((int)d[pk_n + lb] - (int)d[pk_n + la]);
        // (b,k) and (k,b)
        delta += (int)f[b * n + k] * ((int)d[la_n + pk] - (int)d[lb_n + pk]);
        delta += (int)f[k * n + b] * ((int)d[pk_n + la] - (int)d[pk_n + lb]);
    }
    // Diagonal and cross terms
    delta += (int)f[a * n + a] * ((int)d[lb_n + lb] - (int)d[la_n + la]);
    delta += (int)f[b * n + b] * ((int)d[la_n + la] - (int)d[lb_n + lb]);
    delta += (int)f[a * n + b] * ((int)d[lb_n + la] - (int)d[la_n + lb]);
    delta += (int)f[b * n + a] * ((int)d[la_n + lb] - (int)d[lb_n + la]);

    return delta;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n = fs.nextInt();
    if (n <= 0) {
        return 0;
    }

    vector<uint8_t> D(n * n), F(n * n);
    for (int i = 0; i < n; ++i) {
        int base = i * n;
        for (int j = 0; j < n; ++j) {
            int x = fs.nextInt();
            D[base + j] = (uint8_t)x;
        }
    }
    for (int i = 0; i < n; ++i) {
        int base = i * n;
        for (int j = 0; j < n; ++j) {
            int x = fs.nextInt();
            F[base + j] = (uint8_t)x;
        }
    }

    // Degree computations
    vector<int> outD(n, 0), inD(n, 0), outF(n, 0), inF(n, 0);
    long long totalFlow = 0;
    for (int i = 0; i < n; ++i) {
        int base = i * n;
        for (int j = 0; j < n; ++j) {
            int fd = F[base + j];
            outF[i] += fd;
            inF[j] += fd;
            totalFlow += fd;
        }
    }
    for (int i = 0; i < n; ++i) {
        int base = i * n;
        for (int j = 0; j < n; ++j) {
            int dd = D[base + j];
            outD[i] += dd;
            inD[j] += dd;
        }
    }

    vector<int> diagD(n), diagF(n);
    for (int i = 0; i < n; ++i) {
        diagD[i] = D[i * n + i];
        diagF[i] = F[i * n + i];
    }

    auto make_perm = [&](const vector<long long>& wF, const vector<long long>& wD) {
        vector<int> idxF(n), idxD(n);
        iota(idxF.begin(), idxF.end(), 0);
        iota(idxD.begin(), idxD.end(), 0);
        stable_sort(idxF.begin(), idxF.end(), [&](int a, int b) {
            if (wF[a] != wF[b]) return wF[a] > wF[b];
            if (outF[a] + inF[a] != outF[b] + inF[b]) return outF[a] + inF[a] > outF[b] + inF[b];
            if (outF[a] != outF[b]) return outF[a] > outF[b];
            if (inF[a] != inF[b]) return inF[a] > inF[b];
            return a < b;
        });
        stable_sort(idxD.begin(), idxD.end(), [&](int a, int b) {
            if (wD[a] != wD[b]) return wD[a] < wD[b];
            if (outD[a] + inD[a] != outD[b] + inD[b]) return outD[a] + inD[a] < outD[b] + inD[b];
            if (outD[a] != outD[b]) return outD[a] < outD[b];
            if (inD[a] != inD[b]) return inD[a] < inD[b];
            return a < b;
        });
        vector<int> p(n);
        for (int k = 0; k < n; ++k) p[idxF[k]] = idxD[k];
        return p;
    };

    // Generate several initial candidates
    vector<vector<int>> candidates;
    {
        vector<long long> wF(n), wD(n);
        for (int i = 0; i < n; ++i) {
            wF[i] = 1LL * outF[i] + 1LL * inF[i] + 2LL * diagF[i];
            wD[i] = 1LL * outD[i] + 1LL * inD[i] + 2LL * diagD[i];
        }
        candidates.push_back(make_perm(wF, wD));
    }
    {
        vector<long long> wF(n), wD(n);
        for (int i = 0; i < n; ++i) {
            wF[i] = 2LL * outF[i] + 1LL * diagF[i] + 1LL * inF[i];
            wD[i] = 2LL * outD[i] + 1LL * diagD[i] + 1LL * inD[i];
        }
        candidates.push_back(make_perm(wF, wD));
    }
    {
        vector<long long> wF(n), wD(n);
        for (int i = 0; i < n; ++i) {
            wF[i] = 2LL * inF[i] + 1LL * diagF[i] + 1LL * outF[i];
            wD[i] = 2LL * inD[i] + 1LL * diagD[i] + 1LL * outD[i];
        }
        candidates.push_back(make_perm(wF, wD));
    }
    {
        vector<long long> wF(n), wD(n);
        for (int i = 0; i < n; ++i) {
            wF[i] = 3LL * outF[i] + 3LL * inF[i] + 4LL * diagF[i];
            wD[i] = 3LL * outD[i] + 3LL * inD[i] + 4LL * diagD[i];
        }
        candidates.push_back(make_perm(wF, wD));
    }

    // Randomized candidate: shuffle locations against a sorted facilities order
    {
        vector<long long> wF(n);
        for (int i = 0; i < n; ++i) wF[i] = 2LL * outF[i] + 2LL * inF[i] + 3LL * diagF[i];
        vector<int> idxF(n);
        iota(idxF.begin(), idxF.end(), 0);
        stable_sort(idxF.begin(), idxF.end(), [&](int a, int b) {
            if (wF[a] != wF[b]) return wF[a] > wF[b];
            if (outF[a] + inF[a] != outF[b] + inF[b]) return outF[a] + inF[a] > outF[b] + inF[b];
            if (outF[a] != outF[b]) return outF[a] > outF[b];
            if (inF[a] != inF[b]) return inF[a] > inF[b];
            return a < b;
        });
        vector<int> idxD(n);
        iota(idxD.begin(), idxD.end(), 0);
        // Shuffle locations
        mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());
        shuffle(idxD.begin(), idxD.end(), rng);
        vector<int> p(n);
        for (int k = 0; k < n; ++k) p[idxF[k]] = idxD[k];
        candidates.push_back(move(p));
    }

    // Select best candidate by cost
    int best_cost = INT_MAX;
    vector<int> best_p;
    for (auto &p : candidates) {
        int c = compute_cost(p, D, F, n);
        if (c < best_cost) {
            best_cost = c;
            best_p = p;
        }
    }

    // Local search (random pairwise swaps)
    auto start_time = chrono::high_resolution_clock::now();
    const double TIME_LIMIT_SEC = 1.7; // conservative budget
    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    vector<int>& p = best_p;
    int cost = best_cost;

    uniform_int_distribution<int> dist(0, n - 1);
    int iter = 0;
    int no_improve = 0;

    // Precompute a list of facilities ordered by decreasing "importance"
    vector<int> imp_idx(n);
    iota(imp_idx.begin(), imp_idx.end(), 0);
    stable_sort(imp_idx.begin(), imp_idx.end(), [&](int a, int b) {
        int wa = outF[a] + inF[a] + 2 * diagF[a];
        int wb = outF[b] + inF[b] + 2 * diagF[b];
        if (wa != wb) return wa > wb;
        if (outF[a] != outF[b]) return outF[a] > outF[b];
        if (inF[a] != inF[b]) return inF[a] > inF[b];
        return a < b;
    });

    // Candidate lists: for each facility take a small set of others (mix of top-degree and random)
    int CL = max(10, min(40, n / 50 + 10)); // candidate list size
    vector<vector<int>> cand(n);
    for (int i = 0; i < n; ++i) {
        vector<pair<int,int>> tmp;
        tmp.reserve(n);
        for (int j = 0; j < n; ++j) {
            if (i == j) continue;
            int sim = abs(outF[i] - outF[j]) + abs(inF[i] - inF[j]);
            tmp.emplace_back(sim, j);
        }
        nth_element(tmp.begin(), tmp.begin() + min(CL, (int)tmp.size()), tmp.end());
        int take = min(CL, (int)tmp.size());
        cand[i].reserve(take);
        for (int k = 0; k < take; ++k) cand[i].push_back(tmp[k].second);
    }

    while (true) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - start_time).count();
        if (elapsed > TIME_LIMIT_SEC) break;

        bool improved = false;

        // Sweep through a subset of facilities
        int sweepCount = min(n, 200);
        for (int s = 0; s < sweepCount; ++s) {
            int a = imp_idx[dist(rng) % n];
            int best_b = -1;
            int best_delta = 0;

            // Try random picks + candidate list
            int tries = 0;
            int randTries = 5;
            while (tries < randTries) {
                int b = dist(rng);
                if (b == a) continue;
                int d = delta_swap(a, b, p, D, F, n);
                if (d < best_delta) {
                    best_delta = d;
                    best_b = b;
                }
                ++tries;
            }
            // Try candidate list
            for (int b : cand[a]) {
                int d = delta_swap(a, b, p, D, F, n);
                if (d < best_delta) {
                    best_delta = d;
                    best_b = b;
                }
            }

            if (best_b != -1 && best_delta < 0) {
                swap(p[a], p[best_b]);
                cost += best_delta;
                improved = true;
            }

            now = chrono::high_resolution_clock::now();
            elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > TIME_LIMIT_SEC) break;
        }

        iter++;
        if (!improved) {
            no_improve++;
            if (no_improve >= 2) break;
        } else {
            no_improve = 0;
        }
    }

    // Output permutation (1-based)
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}