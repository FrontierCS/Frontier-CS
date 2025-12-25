#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct Cat {
    string name;
    ll q, v, m, l;
};

struct Package {
    int type;
    int cnt;
    ll value;
    int sm, sl;
};

struct Solution {
    vector<ll> cnts;
    ll val;
    ll mass;
    ll vol;
};

static const ll MAX_MASS = 20LL * 1000000LL; // 20 kg in mg
static const ll MAX_VOL  = 25LL * 1000000LL; // 25 L in uL

string inputStr;
size_t posPtr = 0;

void skipWS() {
    while (posPtr < inputStr.size() && isspace((unsigned char)inputStr[posPtr])) posPtr++;
}

ll parseLL() {
    skipWS();
    int sign = 1;
    if (posPtr < inputStr.size() && (inputStr[posPtr] == '-' || inputStr[posPtr] == '+')) {
        if (inputStr[posPtr] == '-') sign = -1;
        posPtr++;
    }
    ll val = 0;
    while (posPtr < inputStr.size() && isdigit((unsigned char)inputStr[posPtr])) {
        val = val * 10 + (inputStr[posPtr] - '0');
        posPtr++;
    }
    return sign * val;
}

vector<Cat> parseInput() {
    vector<Cat> cats;
    skipWS();
    if (posPtr < inputStr.size() && inputStr[posPtr] == '{') posPtr++;
    while (true) {
        skipWS();
        if (posPtr >= inputStr.size()) break;
        if (inputStr[posPtr] == '}') {
            posPtr++;
            break;
        }
        // parse key
        if (inputStr[posPtr] != '"') break;
        posPtr++;
        size_t start = posPtr;
        while (posPtr < inputStr.size() && inputStr[posPtr] != '"') posPtr++;
        string key = inputStr.substr(start, posPtr - start);
        if (posPtr < inputStr.size() && inputStr[posPtr] == '"') posPtr++;
        skipWS();
        if (posPtr < inputStr.size() && inputStr[posPtr] == ':') posPtr++;
        skipWS();
        if (posPtr < inputStr.size() && inputStr[posPtr] == '[') posPtr++;

        ll q = parseLL();
        skipWS();
        if (posPtr < inputStr.size() && inputStr[posPtr] == ',') posPtr++;
        ll v = parseLL();
        skipWS();
        if (posPtr < inputStr.size() && inputStr[posPtr] == ',') posPtr++;
        ll m = parseLL();
        skipWS();
        if (posPtr < inputStr.size() && inputStr[posPtr] == ',') posPtr++;
        ll l = parseLL();
        skipWS();
        if (posPtr < inputStr.size() && inputStr[posPtr] == ']') posPtr++;
        skipWS();
        if (posPtr < inputStr.size() && inputStr[posPtr] == ',') posPtr++;

        Cat c;
        c.name = key;
        c.q = q;
        c.v = v;
        c.m = m;
        c.l = l;
        cats.push_back(c);
    }
    return cats;
}

Solution solveDP(const vector<Cat>& cats) {
    int n = (int)cats.size();
    const int TARGET = 200;

    ll M = MAX_MASS;
    ll L = MAX_VOL;

    ll fMass = max(1LL, (M + TARGET - 1) / TARGET); // ceil(M/TARGET)
    ll fVol  = max(1LL, (L + TARGET - 1) / TARGET);

    int sM = (int)(M / fMass); // <= TARGET
    int sL = (int)(L / fVol);  // <= TARGET

    int width = sL + 1;
    int S = (sM + 1) * (sL + 1);

    vector<Package> pkgs;
    pkgs.reserve(n * 16);

    for (int i = 0; i < n; ++i) {
        ll q = cats[i].q;
        ll remain = q;
        ll k = 1;
        while (remain > 0) {
            ll cnt = min(k, remain);
            ll mass = cats[i].m * cnt;
            ll vol = cats[i].l * cnt;
            if (mass <= M && vol <= L) {
                int sm = (int)((mass + fMass - 1) / fMass);
                int sl = (int)((vol + fVol - 1) / fVol);
                if (sm <= sM && sl <= sL) {
                    Package p;
                    p.type = i;
                    p.cnt = (int)cnt;
                    p.value = cats[i].v * cnt;
                    p.sm = sm;
                    p.sl = sl;
                    pkgs.push_back(p);
                }
            }
            remain -= cnt;
            k <<= 1;
        }
    }

    int P = (int)pkgs.size();
    const ll NEG_INF = (ll)-4e18;

    vector<ll> dp(S, NEG_INF);
    dp[0] = 0;
    vector<unsigned char> choose((size_t)P * (size_t)S, 0);

    for (int p = 0; p < P; ++p) {
        int wM = pkgs[p].sm;
        int wL = pkgs[p].sl;
        ll val = pkgs[p].value;
        for (int m = sM; m >= wM; --m) {
            int baseRow = m * width;
            int prevRow = (m - wM) * width;
            for (int l = sL; l >= wL; --l) {
                int idx = baseRow + l;
                int prev = prevRow + (l - wL);
                ll prevVal = dp[prev];
                if (prevVal == NEG_INF) continue;
                ll cand = prevVal + val;
                if (cand > dp[idx]) {
                    dp[idx] = cand;
                    choose[(size_t)p * (size_t)S + (size_t)idx] = 1;
                }
            }
        }
    }

    ll bestVal = 0;
    int bestIdx = 0;
    for (int idx = 0; idx < S; ++idx) {
        if (dp[idx] > bestVal) {
            bestVal = dp[idx];
            bestIdx = idx;
        }
    }

    vector<ll> cnts(n, 0);
    int curM = bestIdx / width;
    int curL = bestIdx % width;

    for (int p = P - 1; p >= 0; --p) {
        int idx = curM * width + curL;
        if (choose[(size_t)p * (size_t)S + (size_t)idx]) {
            cnts[pkgs[p].type] += pkgs[p].cnt;
            curM -= pkgs[p].sm;
            curL -= pkgs[p].sl;
        }
    }

    Solution sol;
    sol.cnts = cnts;
    sol.mass = 0;
    sol.vol = 0;
    sol.val = 0;
    for (int i = 0; i < n; ++i) {
        sol.mass += sol.cnts[i] * cats[i].m;
        sol.vol  += sol.cnts[i] * cats[i].l;
        sol.val  += sol.cnts[i] * cats[i].v;
    }
    // Feasibility should hold by construction.
    if (sol.mass > M || sol.vol > L) {
        // Safety fallback: zero solution
        sol.cnts.assign(n, 0);
        sol.mass = sol.vol = sol.val = 0;
    }
    return sol;
}

Solution greedyFill(const vector<Cat>& cats,
                    const vector<ll>& baseCnt,
                    ll baseMass, ll baseVol, ll baseVal,
                    int mode) {
    int n = (int)cats.size();
    Solution sol;
    sol.cnts = baseCnt;
    sol.mass = baseMass;
    sol.vol = baseVol;
    sol.val = baseVal;

    if (sol.mass > MAX_MASS || sol.vol > MAX_VOL) {
        // invalid base; return as is
        return sol;
    }

    vector<ll> remaining(n);
    for (int i = 0; i < n; ++i) {
        ll rem = cats[i].q - baseCnt[i];
        if (rem < 0) rem = 0;
        remaining[i] = rem;
    }

    vector<int> idxs;
    idxs.reserve(n);
    for (int i = 0; i < n; ++i) {
        if (remaining[i] > 0) idxs.push_back(i);
    }
    if (idxs.empty()) return sol;

    vector<double> score(n, 0.0);
    for (int i : idxs) {
        double s = 0.0;
        double d1 = (double)cats[i].m / (double)MAX_MASS;
        double d2 = (double)cats[i].l / (double)MAX_VOL;
        switch (mode) {
            case 0: // normalized sum
                s = (double)cats[i].v / (d1 + d2);
                break;
            case 1: // value per mass
                s = (double)cats[i].v / (double)cats[i].m;
                break;
            case 2: // value per volume
                s = (double)cats[i].v / (double)cats[i].l;
                break;
            case 3: { // value per max normalized
                double d = max(d1, d2);
                s = (double)cats[i].v / d;
                break;
            }
            default:
                s = (double)cats[i].v / (d1 + d2);
                break;
        }
        score[i] = s;
    }

    sort(idxs.begin(), idxs.end(), [&](int a, int b) {
        if (score[a] == score[b]) return cats[a].v > cats[b].v;
        return score[a] > score[b];
    });

    for (int i : idxs) {
        if (remaining[i] <= 0) continue;
        if (sol.mass >= MAX_MASS || sol.vol >= MAX_VOL) break;
        ll maxByMass = (cats[i].m > 0) ? ( (MAX_MASS - sol.mass) / cats[i].m ) : remaining[i];
        ll maxByVol  = (cats[i].l > 0) ? ( (MAX_VOL  - sol.vol ) / cats[i].l ) : remaining[i];
        ll canTake = min(remaining[i], min(maxByMass, maxByVol));
        if (canTake <= 0) continue;
        sol.cnts[i] += canTake;
        sol.mass += canTake * cats[i].m;
        sol.vol  += canTake * cats[i].l;
        sol.val  += canTake * cats[i].v;
    }

    return sol;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    inputStr.assign((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    vector<Cat> cats = parseInput();
    int n = (int)cats.size();

    vector<ll> emptyCnt(n, 0);

    Solution best;
    best.cnts = emptyCnt;
    best.mass = 0;
    best.vol = 0;
    best.val = 0;

    // Greedy from empty with various heuristics
    for (int mode = 0; mode <= 3; ++mode) {
        Solution cand = greedyFill(cats, emptyCnt, 0, 0, 0, mode);
        if (cand.mass <= MAX_MASS && cand.vol <= MAX_VOL && cand.val > best.val) {
            best = cand;
        }
    }

    // DP-based solution + greedy refinements
    Solution dpSol = solveDP(cats);
    for (int mode = 0; mode <= 3; ++mode) {
        Solution cand = greedyFill(cats, dpSol.cnts, dpSol.mass, dpSol.vol, dpSol.val, mode);
        if (cand.mass <= MAX_MASS && cand.vol <= MAX_VOL && cand.val > best.val) {
            best = cand;
        }
    }

    // Output JSON with same key order
    cout << "{\n";
    for (int i = 0; i < n; ++i) {
        cout << " \"" << cats[i].name << "\": " << best.cnts[i];
        if (i + 1 < n) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";

    return 0;
}