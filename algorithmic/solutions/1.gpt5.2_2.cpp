#include <bits/stdc++.h>
using namespace std;

static const long long CAP_M = 20LL * 1000 * 1000; // mg
static const long long CAP_V = 25LL * 1000 * 1000; // uL

struct Cat {
    string name;
    int q;
    long long v, m, l;
};

struct Piece {
    int type;
    int cnt;
    int wm, wv;
    long long val;
};

struct Sol {
    vector<int> cnt;
    long long value = 0;
    long long mass = 0;
    long long vol = 0;
    bool feasible = false;
};

struct Parser {
    string s;
    size_t i = 0;

    explicit Parser(string in): s(std::move(in)) {}

    void skipws() {
        while (i < s.size() && (unsigned char)s[i] <= 32) i++;
    }

    bool consume(char c) {
        skipws();
        if (i < s.size() && s[i] == c) { i++; return true; }
        return false;
    }

    void expect(char c) {
        skipws();
        if (i >= s.size() || s[i] != c) {
            // Attempt to proceed anyway
            return;
        }
        i++;
    }

    string parseString() {
        skipws();
        expect('"');
        string out;
        while (i < s.size() && s[i] != '"') {
            // keys are lowercase ascii, no escapes per statement
            out.push_back(s[i++]);
        }
        expect('"');
        return out;
    }

    long long parseInt() {
        skipws();
        long long sign = 1;
        if (i < s.size() && s[i] == '-') { sign = -1; i++; }
        long long x = 0;
        while (i < s.size() && isdigit((unsigned char)s[i])) {
            x = x * 10 + (s[i++] - '0');
        }
        return x * sign;
    }
};

static inline long long calcValue(const vector<Cat>& cats, const vector<int>& cnt) {
    long long v = 0;
    for (size_t i = 0; i < cats.size(); i++) v += (long long)cnt[i] * cats[i].v;
    return v;
}
static inline long long calcMass(const vector<Cat>& cats, const vector<int>& cnt) {
    long long m = 0;
    for (size_t i = 0; i < cats.size(); i++) m += (long long)cnt[i] * cats[i].m;
    return m;
}
static inline long long calcVol(const vector<Cat>& cats, const vector<int>& cnt) {
    long long l = 0;
    for (size_t i = 0; i < cats.size(); i++) l += (long long)cnt[i] * cats[i].l;
    return l;
}
static inline bool feasible(const vector<Cat>& cats, const vector<int>& cnt) {
    return calcMass(cats, cnt) <= CAP_M && calcVol(cats, cnt) <= CAP_V;
}

static void repairFeasible(const vector<Cat>& cats, vector<int>& cnt) {
    long long mass = calcMass(cats, cnt);
    long long vol = calcVol(cats, cnt);

    int guard = 0;
    while ((mass > CAP_M || vol > CAP_V) && guard++ < 100000) {
        long long dm = max(0LL, mass - CAP_M);
        long long dv = max(0LL, vol - CAP_V);
        double a = (dm > 0) ? (double)dm / (double)CAP_M : 0.0;
        double b = (dv > 0) ? (double)dv / (double)CAP_V : 0.0;

        int best = -1;
        double worstDen = 1e300;
        for (int i = 0; i < (int)cats.size(); i++) {
            if (cnt[i] <= 0) continue;
            double denom = a * (double)cats[i].m + b * (double)cats[i].l;
            if (denom <= 0) denom = 1e-18;
            double dens = (double)cats[i].v / denom; // value per weighted resource
            if (dens < worstDen) {
                worstDen = dens;
                best = i;
            }
        }
        if (best == -1) break;

        long long need = 1;
        if (dm > 0) need = max(need, (dm + cats[best].m - 1) / cats[best].m);
        if (dv > 0) need = max(need, (dv + cats[best].l - 1) / cats[best].l);
        need = min<long long>(need, cnt[best]);
        if (need <= 0) break;

        cnt[best] -= (int)need;
        mass -= need * cats[best].m;
        vol  -= need * cats[best].l;
    }
}

static void greedyFill(const vector<Cat>& cats, vector<int>& cnt) {
    long long mass = calcMass(cats, cnt);
    long long vol = calcVol(cats, cnt);
    if (mass > CAP_M || vol > CAP_V) repairFeasible(cats, cnt), mass = calcMass(cats, cnt), vol = calcVol(cats, cnt);

    long long remM = CAP_M - mass;
    long long remV = CAP_V - vol;
    int guard = 0;

    while (guard++ < 20000) {
        int best = -1;
        double bestScore = -1.0;

        for (int i = 0; i < (int)cats.size(); i++) {
            if (cnt[i] >= cats[i].q) continue;
            if (cats[i].m > remM || cats[i].l > remV) continue;

            double cost = 0.0;
            if (remM > 0) cost += (double)cats[i].m / (double)remM;
            else cost += 1e9;
            if (remV > 0) cost += (double)cats[i].l / (double)remV;
            else cost += 1e9;

            double score = (double)cats[i].v / (cost + 1e-18);
            if (score > bestScore) {
                bestScore = score;
                best = i;
            }
        }
        if (best == -1) break;

        long long add = cats[best].q - cnt[best];
        add = min(add, remM / cats[best].m);
        add = min(add, remV / cats[best].l);
        if (add <= 0) break;

        cnt[best] += (int)add;
        remM -= add * cats[best].m;
        remV -= add * cats[best].l;
    }
}

static void localImproveSingleInsert(const vector<Cat>& cats, vector<int>& cnt, int maxIters = 5000) {
    repairFeasible(cats, cnt);
    greedyFill(cats, cnt);
    long long mass = calcMass(cats, cnt);
    long long vol  = calcVol(cats, cnt);
    long long val  = calcValue(cats, cnt);

    for (int iter = 0; iter < maxIters; iter++) {
        long long remM = CAP_M - mass;
        long long remV = CAP_V - vol;

        long long bestDelta = 0;
        int bestAdd = -1;
        int bestRem = -1;
        int bestRemQty = 0;

        for (int a = 0; a < (int)cats.size(); a++) {
            if (cnt[a] >= cats[a].q) continue;

            long long needM = max(0LL, cats[a].m - remM);
            long long needV = max(0LL, cats[a].l - remV);

            if (needM == 0 && needV == 0) {
                long long delta = cats[a].v;
                if (delta > bestDelta) {
                    bestDelta = delta;
                    bestAdd = a;
                    bestRem = -1;
                    bestRemQty = 0;
                }
                continue;
            }

            for (int r = 0; r < (int)cats.size(); r++) {
                if (r == a) continue;
                if (cnt[r] <= 0) continue;
                long long qty = 1;
                if (needM > 0) qty = max(qty, (needM + cats[r].m - 1) / cats[r].m);
                if (needV > 0) qty = max(qty, (needV + cats[r].l - 1) / cats[r].l);
                if (qty > cnt[r]) continue;

                long long newMass = mass + cats[a].m - qty * cats[r].m;
                long long newVol  = vol  + cats[a].l - qty * cats[r].l;
                if (newMass > CAP_M || newVol > CAP_V) continue;
                if (newMass < 0 || newVol < 0) continue;

                long long delta = cats[a].v - qty * cats[r].v;
                if (delta > bestDelta) {
                    bestDelta = delta;
                    bestAdd = a;
                    bestRem = r;
                    bestRemQty = (int)qty;
                }
            }
        }

        if (bestDelta <= 0) break;

        cnt[bestAdd] += 1;
        mass += cats[bestAdd].m;
        vol  += cats[bestAdd].l;
        val  += cats[bestAdd].v;

        if (bestRem != -1 && bestRemQty > 0) {
            cnt[bestRem] -= bestRemQty;
            mass -= (long long)bestRemQty * cats[bestRem].m;
            vol  -= (long long)bestRemQty * cats[bestRem].l;
            val  -= (long long)bestRemQty * cats[bestRem].v;
        }

        if (mass > CAP_M || vol > CAP_V) {
            repairFeasible(cats, cnt);
            mass = calcMass(cats, cnt);
            vol  = calcVol(cats, cnt);
            val  = calcValue(cats, cnt);
        }

        // Occasionally fill remaining
        if ((iter & 31) == 31) {
            greedyFill(cats, cnt);
            mass = calcMass(cats, cnt);
            vol  = calcVol(cats, cnt);
            val  = calcValue(cats, cnt);
        }
    }
}

static Sol makeSol(const vector<Cat>& cats, vector<int> cnt) {
    for (int i = 0; i < (int)cats.size(); i++) {
        if (cnt[i] < 0) cnt[i] = 0;
        if (cnt[i] > cats[i].q) cnt[i] = cats[i].q;
    }
    repairFeasible(cats, cnt);
    greedyFill(cats, cnt);
    localImproveSingleInsert(cats, cnt, 2000);

    Sol s;
    s.cnt = std::move(cnt);
    s.mass = calcMass(cats, s.cnt);
    s.vol = calcVol(cats, s.cnt);
    s.value = calcValue(cats, s.cnt);
    s.feasible = (s.mass <= CAP_M && s.vol <= CAP_V);
    return s;
}

static Sol greedyHeuristic(const vector<Cat>& cats, double a, double b) {
    int n = (int)cats.size();
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    auto score = [&](int i)->double {
        double denom = a * (double)cats[i].m + b * (double)cats[i].l;
        if (denom <= 0) denom = 1e-18;
        return (double)cats[i].v / denom;
    };
    sort(order.begin(), order.end(), [&](int i, int j){
        double si = score(i), sj = score(j);
        if (si != sj) return si > sj;
        return cats[i].v > cats[j].v;
    });

    vector<int> cnt(n, 0);
    long long remM = CAP_M, remV = CAP_V;

    for (int idx : order) {
        if (remM <= 0 || remV <= 0) break;
        long long can = cats[idx].q;
        can = min(can, remM / cats[idx].m);
        can = min(can, remV / cats[idx].l);
        if (can <= 0) continue;
        cnt[idx] = (int)can;
        remM -= can * cats[idx].m;
        remV -= can * cats[idx].l;
    }

    return makeSol(cats, cnt);
}

static Sol dpHeuristicScaled(const vector<Cat>& cats, int sM, int sV) {
    int n = (int)cats.size();

    int capM = (int)((CAP_M + sM - 1) / sM); // ceil
    int capV = (int)((CAP_V + sV - 1) / sV); // ceil
    if (capM < 0) capM = 0;
    if (capV < 0) capV = 0;

    vector<Piece> items;
    items.reserve(256);

    for (int i = 0; i < n; i++) {
        long long maxK = cats[i].q;
        long long limM = (CAP_M + sM) / cats[i].m;
        long long limV = (CAP_V + sV) / cats[i].l;
        maxK = min(maxK, limM);
        maxK = min(maxK, limV);
        if (maxK <= 0) continue;

        long long rem = maxK;
        long long p = 1;
        while (rem > 0) {
            long long take = min(p, rem);
            rem -= take;
            p <<= 1;

            long long mm = take * cats[i].m;
            long long vv = take * cats[i].l;
            int wm = (int)((mm + sM - 1) / sM);
            int wv = (int)((vv + sV - 1) / sV);
            if (wm > capM || wv > capV) continue;

            Piece pc;
            pc.type = i;
            pc.cnt = (int)take;
            pc.wm = wm;
            pc.wv = wv;
            pc.val = take * cats[i].v;
            items.push_back(pc);
        }
    }

    int W = capM, V = capV;
    int rowLen = V + 1;
    int S = (W + 1) * rowLen;

    vector<long long> dp(S, -1);
    vector<int> prev(S, -1);
    vector<int> take(S, -1);

    dp[0] = 0;

    for (int it = 0; it < (int)items.size(); it++) {
        const auto &I = items[it];
        for (int i = W; i >= I.wm; --i) {
            int row = i * rowLen;
            int prow = (i - I.wm) * rowLen;

            long long* dpRow = dp.data() + row;
            long long* dpP   = dp.data() + prow;

            int* prevRow = prev.data() + row;
            int* takeRow = take.data() + row;

            for (int j = V; j >= I.wv; --j) {
                int jp = j - I.wv;
                long long base = dpP[jp];
                if (base < 0) continue;
                long long cand = base + I.val;
                if (cand > dpRow[j]) {
                    dpRow[j] = cand;
                    prevRow[j] = prow + jp;
                    takeRow[j] = it;
                }
            }
        }
    }

    int bestIdx = 0;
    long long bestVal = 0;
    for (int idx = 0; idx < S; idx++) {
        long long v = dp[idx];
        if (v > bestVal) {
            bestVal = v;
            bestIdx = idx;
        }
    }

    vector<int> cnt(n, 0);
    int cur = bestIdx;
    int guard = 0;
    while (cur != 0 && cur >= 0 && guard++ < 1000000) {
        int it = take[cur];
        if (it < 0) break;
        cnt[items[it].type] += items[it].cnt;
        cur = prev[cur];
        if (cur < 0) break;
    }

    for (int i = 0; i < n; i++) if (cnt[i] > cats[i].q) cnt[i] = cats[i].q;
    return makeSol(cats, cnt);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    Parser p(input);

    vector<Cat> cats;
    cats.reserve(12);

    p.skipws();
    p.expect('{');

    while (true) {
        p.skipws();
        if (p.consume('}')) break;
        string key = p.parseString();
        p.skipws();
        p.expect(':');
        p.skipws();
        p.expect('[');
        long long q = p.parseInt();
        p.skipws(); p.consume(',');
        long long v = p.parseInt();
        p.skipws(); p.consume(',');
        long long m = p.parseInt();
        p.skipws(); p.consume(',');
        long long l = p.parseInt();
        p.skipws();
        p.expect(']');

        Cat c;
        c.name = key;
        c.q = (int)q;
        c.v = v;
        c.m = m;
        c.l = l;
        cats.push_back(c);

        p.skipws();
        if (p.consume(',')) continue;
        p.skipws();
        if (p.consume('}')) break;
    }

    int n = (int)cats.size();
    if (n == 0) {
        cout << "{}\n";
        return 0;
    }

    auto start = chrono::steady_clock::now();

    Sol best;
    best.cnt.assign(n, 0);
    best.value = 0;
    best.mass = 0;
    best.vol = 0;
    best.feasible = true;

    auto consider = [&](const Sol& s) {
        if (!s.feasible) return;
        if (s.value > best.value) best = s;
    };

    // Greedy variants
    vector<pair<double,double>> weights = {
        {1.0, 1.0},
        {2.0, 1.0},
        {1.0, 2.0},
        {3.0, 1.0},
        {1.0, 3.0},
        {1.0, 0.5},
        {0.5, 1.0},
        {0.2, 1.8},
        {1.0, 0.0},
        {0.0, 1.0}
    };
    for (auto [a,b] : weights) {
        auto now = chrono::steady_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(now - start).count() > 850) break;
        consider(greedyHeuristic(cats, a, b));
    }

    // DP scaling attempts
    vector<pair<int,int>> scales = {
        {25000, 25000},
        {40000, 40000}
    };
    for (auto [sM, sV] : scales) {
        auto now = chrono::steady_clock::now();
        if (chrono::duration_cast<chrono::milliseconds>(now - start).count() > 850) break;
        consider(dpHeuristicScaled(cats, sM, sV));
    }

    // Final repair (safety)
    for (int i = 0; i < n; i++) {
        if (best.cnt[i] < 0) best.cnt[i] = 0;
        if (best.cnt[i] > cats[i].q) best.cnt[i] = cats[i].q;
    }
    repairFeasible(cats, best.cnt);

    // Output JSON with same keys as input order
    cout << "{\n";
    for (int i = 0; i < n; i++) {
        cout << " " << "\"" << cats[i].name << "\": " << best.cnt[i];
        if (i + 1 < n) cout << ",";
        cout << "\n";
    }
    cout << "}\n";
    return 0;
}