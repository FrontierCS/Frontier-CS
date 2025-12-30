#include <bits/stdc++.h>
using namespace std;

struct Pt {
    int x, y;
};

struct Rect {
    int x1, x2, y1, y2; // inclusive boundaries
};

static inline long long enc(int x, int y) {
    return (static_cast<long long>(x) << 20) ^ static_cast<long long>(y);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    const int M = 2 * N;
    vector<int> xs(M), ys(M);
    vector<int> w(M);
    vector<Pt> macks(N), sards(N);

    unordered_set<long long> occ;
    occ.reserve((size_t)M * 2);

    for (int i = 0; i < M; i++) {
        int x, y;
        cin >> x >> y;
        xs[i] = x;
        ys[i] = y;
        occ.insert(enc(x, y));
        if (i < N) {
            w[i] = +1;
            macks[i] = {x, y};
        } else {
            w[i] = -1;
            sards[i - N] = {x, y};
        }
    }

    auto clampRect = [](Rect r) -> Rect {
        r.x1 = max(0, min(100000, r.x1));
        r.x2 = max(0, min(100000, r.x2));
        r.y1 = max(0, min(100000, r.y1));
        r.y2 = max(0, min(100000, r.y2));
        if (r.x1 > r.x2) swap(r.x1, r.x2);
        if (r.y1 > r.y2) swap(r.y1, r.y2);
        if (r.x1 == r.x2) {
            if (r.x1 > 0) r.x1--;
            else if (r.x2 < 100000) r.x2++;
        }
        if (r.y1 == r.y2) {
            if (r.y1 > 0) r.y1--;
            else if (r.y2 < 100000) r.y2++;
        }
        return r;
    };

    auto evalRect = [&](const Rect& r) -> int {
        int sum = 0;
        const int x1 = r.x1, x2 = r.x2, y1 = r.y1, y2 = r.y2;
        for (int i = 0; i < M; i++) {
            int x = xs[i], y = ys[i];
            if (x1 <= x && x <= x2 && y1 <= y && y <= y2) sum += w[i];
        }
        return sum;
    };

    // Baseline rectangle: whole area
    Rect best = {0, 100000, 0, 100000};
    best = clampRect(best);
    int bestSum = evalRect(best);

    // Also consider empty-ish small rectangles near corners (likely empty)
    auto tryEmptyCandidate = [&](int x, int y) {
        Rect r = {x, x + 1, y, y + 1};
        r = clampRect(r);
        int s = evalRect(r);
        if (s > bestSum) {
            bestSum = s;
            best = r;
        }
    };
    tryEmptyCandidate(0, 0);
    tryEmptyCandidate(99998, 0);
    tryEmptyCandidate(0, 99998);
    tryEmptyCandidate(99998, 99998);

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)N * 0x9e3779b97f4a7c15ULL;
    mt19937_64 rng(seed);

    vector<int> sizes = {50, 100, 200, 300, 500, 800, 1200, 2000, 3000, 5000, 8000, 12000, 20000, 30000, 45000, 65000, 90000};
    auto randInt = [&](int lo, int hi) -> int {
        if (lo > hi) swap(lo, hi);
        uniform_int_distribution<int> dist(lo, hi);
        return dist(rng);
    };
    auto randPick = [&](const vector<int>& v) -> int {
        uniform_int_distribution<int> dist(0, (int)v.size() - 1);
        return v[dist(rng)];
    };

    vector<int> mackX(N), mackY(N);
    for (int i = 0; i < N; i++) {
        mackX[i] = macks[i].x;
        mackY[i] = macks[i].y;
    }
    sort(mackX.begin(), mackX.end());
    sort(mackY.begin(), mackY.end());

    auto genRect = [&]() -> Rect {
        int mode = randInt(0, 5);
        Rect r;
        if (mode <= 2) {
            // Around a random mackerel
            const Pt& p = macks[randInt(0, N - 1)];
            int W = randPick(sizes);
            int H = randPick(sizes);
            int dx = randInt(0, W);
            int dy = randInt(0, H);
            r.x1 = p.x - dx;
            r.x2 = r.x1 + W;
            r.y1 = p.y - dy;
            r.y2 = r.y1 + H;
        } else if (mode == 3) {
            // Bounding box of two mackerels with margin
            const Pt& p = macks[randInt(0, N - 1)];
            const Pt& q = macks[randInt(0, N - 1)];
            r.x1 = min(p.x, q.x);
            r.x2 = max(p.x, q.x);
            r.y1 = min(p.y, q.y);
            r.y2 = max(p.y, q.y);
            int mg = randPick(sizes) / 4;
            r.x1 -= randInt(0, mg);
            r.x2 += randInt(0, mg);
            r.y1 -= randInt(0, mg);
            r.y2 += randInt(0, mg);
        } else if (mode == 4) {
            // Percentile-based rectangle from mackerel marginals
            int span = randInt(20, 1200);
            int i1 = randInt(0, N - 1);
            int i2 = min(N - 1, i1 + span);
            int j1 = randInt(0, N - 1);
            int j2 = min(N - 1, j1 + span);
            r.x1 = mackX[i1];
            r.x2 = mackX[i2];
            r.y1 = mackY[j1];
            r.y2 = mackY[j2];
            if (r.x1 == r.x2) r.x2++;
            if (r.y1 == r.y2) r.y2++;
        } else {
            // Random rectangle with random size
            int W = randPick(sizes);
            int H = randPick(sizes);
            int x1 = randInt(0, 100000);
            int y1 = randInt(0, 100000);
            r.x1 = x1;
            r.y1 = y1;
            r.x2 = x1 + W;
            r.y2 = y1 + H;
        }
        r = clampRect(r);
        return r;
    };

    const int ITER = 12000;
    for (int it = 0; it < ITER; it++) {
        Rect r = genRect();
        int s = evalRect(r);
        if (s > bestSum) {
            bestSum = s;
            best = r;
        }
    }

    // Local annealing refinement around best
    Rect cur = best;
    int curSum = bestSum;
    vector<int> steps = {1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000};
    const int SA_STEPS = 2000;
    const double T0 = 5.0, T1 = 0.1;

    for (int t = 0; t < SA_STEPS; t++) {
        double alpha = (double)t / (double)SA_STEPS;
        double T = T0 * pow(T1 / T0, alpha);

        Rect nxt = cur;
        int side = randInt(0, 3);
        int delta = steps[randInt(0, (int)steps.size() - 1)];
        int dir = (randInt(0, 1) ? +1 : -1);

        if (side == 0) nxt.x1 += dir * delta;
        else if (side == 1) nxt.x2 += dir * delta;
        else if (side == 2) nxt.y1 += dir * delta;
        else nxt.y2 += dir * delta;

        nxt = clampRect(nxt);
        int ns = evalRect(nxt);

        bool accept = false;
        if (ns >= curSum) accept = true;
        else {
            double prob = exp((double)(ns - curSum) / T);
            uniform_real_distribution<double> dist(0.0, 1.0);
            if (dist(rng) < prob) accept = true;
        }

        if (accept) {
            cur = nxt;
            curSum = ns;
            if (curSum > bestSum) {
                bestSum = curSum;
                best = cur;
            }
        }
    }

    // If bestSum is negative, attempt to find a tiny empty rectangle (sum=0) and use it.
    if (bestSum < 0) {
        bool found = false;
        for (int tries = 0; tries < 2000 && !found; tries++) {
            int x = randInt(0, 99999);
            int y = randInt(0, 99999);
            bool ok = true;
            ok &= occ.find(enc(x, y)) == occ.end();
            ok &= occ.find(enc(x + 1, y)) == occ.end();
            ok &= occ.find(enc(x, y + 1)) == occ.end();
            ok &= occ.find(enc(x + 1, y + 1)) == occ.end();
            if (ok) {
                best = clampRect({x, x + 1, y, y + 1});
                bestSum = 0;
                found = true;
            }
        }
        if (!found) {
            // Fallback scan
            for (int x = 0; x < 100000 && !found; x++) {
                for (int y = 0; y < 100000 && !found; y++) {
                    bool ok = true;
                    ok &= occ.find(enc(x, y)) == occ.end();
                    ok &= occ.find(enc(x + 1, y)) == occ.end();
                    ok &= occ.find(enc(x, y + 1)) == occ.end();
                    ok &= occ.find(enc(x + 1, y + 1)) == occ.end();
                    if (ok) {
                        best = clampRect({x, x + 1, y, y + 1});
                        bestSum = 0;
                        found = true;
                    }
                }
            }
            if (!found) {
                // Shouldn't happen; use whole area
                best = clampRect({0, 100000, 0, 100000});
                bestSum = evalRect(best);
            }
        }
    }

    best = clampRect(best);

    cout << 4 << "\n";
    cout << best.x1 << " " << best.y1 << "\n";
    cout << best.x2 << " " << best.y1 << "\n";
    cout << best.x2 << " " << best.y2 << "\n";
    cout << best.x1 << " " << best.y2 << "\n";
    return 0;
}