#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    long long q, v, m, l;
    long long max_take;
};

const long long CAP_M = 20000000LL;
const long long CAP_L = 25000000LL;

vector<Item> items;
int n_items = 0;

void parse_input() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string s((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    int len = (int)s.size();
    int pos = 0;

    auto skip_ws = [&]() {
        while (pos < len && isspace((unsigned char)s[pos])) pos++;
    };

    skip_ws();
    if (pos < len && s[pos] == '{') pos++;

    while (pos < len) {
        skip_ws();
        if (pos >= len) break;
        if (s[pos] == '}') { pos++; break; }
        if (s[pos] == ',') { pos++; continue; }

        skip_ws();
        if (pos >= len || s[pos] != '"') break;
        pos++; // skip opening quote
        string name;
        while (pos < len && s[pos] != '"') {
            name.push_back(s[pos]);
            pos++;
        }
        if (pos < len && s[pos] == '"') pos++; // closing quote

        skip_ws();
        if (pos < len && s[pos] == ':') pos++;
        skip_ws();
        if (pos < len && s[pos] == '[') pos++;

        vector<long long> arr;
        arr.reserve(4);
        for (int k = 0; k < 4; k++) {
            skip_ws();
            long long sign = 1;
            if (pos < len && s[pos] == '-') {
                sign = -1;
                pos++;
            }
            long long val = 0;
            while (pos < len && isdigit((unsigned char)s[pos])) {
                val = val * 10 + (s[pos] - '0');
                pos++;
            }
            arr.push_back(sign * val);
            skip_ws();
            if (k < 3 && pos < len && s[pos] == ',') pos++;
        }
        skip_ws();
        if (pos < len && s[pos] == ']') pos++;

        Item it;
        it.name = name;
        it.q = arr[0];
        it.v = arr[1];
        it.m = arr[2];
        it.l = arr[3];
        it.max_take = 0; // to be set later
        items.push_back(it);

        skip_ws();
        if (pos < len && s[pos] == ',') { pos++; continue; }
    }

    n_items = (int)items.size();
}

long long evalSolution(const vector<long long>& x) {
    long long val = 0;
    for (int i = 0; i < n_items; i++) {
        val += x[i] * items[i].v;
    }
    return val;
}

long long greedy_fill(const vector<int>& order, vector<long long>& x, long long& massUsed, long long& volUsed) {
    long long rM = CAP_M - massUsed;
    long long rL = CAP_L - volUsed;
    for (int idx : order) {
        int i = idx;
        if (items[i].max_take <= x[i]) continue;
        long long avail = items[i].max_take - x[i];
        if (avail <= 0) continue;
        if (items[i].m > 0) {
            long long byM = rM / items[i].m;
            if (byM < avail) avail = byM;
        }
        if (items[i].l > 0) {
            long long byL = rL / items[i].l;
            if (byL < avail) avail = byL;
        }
        if (avail <= 0) continue;
        x[i] += avail;
        long long addM = avail * items[i].m;
        long long addL = avail * items[i].l;
        massUsed += addM;
        volUsed += addL;
        rM -= addM;
        rL -= addL;
        if (rM <= 0 || rL <= 0) break;
    }
    return evalSolution(x);
}

void local_search(vector<long long>& x, long long& value, long long& massUsed, long long& volUsed,
                  const vector<int>& refill_order, clock_t t0) {
    const int MAX_ITERS = 100;
    for (int iter = 0; iter < MAX_ITERS; iter++) {
        double elapsed = double(clock() - t0) / CLOCKS_PER_SEC;
        if (elapsed > 0.90) return;

        bool improved = false;
        long long bestVal = value;
        vector<long long> bestX;
        long long bestMass = massUsed, bestVol = volUsed;

        // 1-item removal moves
        for (int i = 0; i < n_items; i++) {
            if (x[i] == 0) continue;
            long long lim = min(10LL, x[i]);
            for (long long rem = 1; rem <= lim; rem++) {
                vector<long long> tmp_x = x;
                tmp_x[i] -= rem;
                long long tmpMass = massUsed - rem * items[i].m;
                long long tmpVol = volUsed - rem * items[i].l;
                long long newVal = greedy_fill(refill_order, tmp_x, tmpMass, tmpVol);
                if (newVal > bestVal) {
                    bestVal = newVal;
                    bestX.swap(tmp_x);
                    bestMass = tmpMass;
                    bestVol = tmpVol;
                    improved = true;
                }
            }
        }

        // 2-item removal moves
        for (int i = 0; i < n_items; i++) {
            if (x[i] == 0) continue;
            long long limi = min(5LL, x[i]);
            for (int j = i + 1; j < n_items; j++) {
                if (x[j] == 0) continue;
                long long limj = min(5LL, x[j]);
                for (long long remi = 1; remi <= limi; remi++) {
                    for (long long remj = 1; remj <= limj; remj++) {
                        vector<long long> tmp_x = x;
                        tmp_x[i] -= remi;
                        tmp_x[j] -= remj;
                        long long tmpMass = massUsed - remi * items[i].m - remj * items[j].m;
                        long long tmpVol = volUsed - remi * items[i].l - remj * items[j].l;
                        long long newVal = greedy_fill(refill_order, tmp_x, tmpMass, tmpVol);
                        if (newVal > bestVal) {
                            bestVal = newVal;
                            bestX.swap(tmp_x);
                            bestMass = tmpMass;
                            bestVol = tmpVol;
                            improved = true;
                        }
                    }
                }
            }
        }

        if (!improved) break;
        x.swap(bestX);
        value = bestVal;
        massUsed = bestMass;
        volUsed = bestVol;
    }
}

vector<int> create_order_from_scores(const vector<long double>& scores, bool descending) {
    vector<int> ord(n_items);
    iota(ord.begin(), ord.end(), 0);
    if (descending) {
        sort(ord.begin(), ord.end(), [&](int a, int b) {
            if (scores[a] == scores[b]) return a < b;
            return scores[a] > scores[b];
        });
    } else {
        sort(ord.begin(), ord.end(), [&](int a, int b) {
            if (scores[a] == scores[b]) return a < b;
            return scores[a] < scores[b];
        });
    }
    return ord;
}

int main() {
    parse_input();
    n_items = (int)items.size();

    // Compute per-item max_take
    for (int i = 0; i < n_items; i++) {
        long long max_by_q = items[i].q;
        long long max_by_m = (items[i].m == 0) ? max_by_q : (CAP_M / items[i].m);
        long long max_by_l = (items[i].l == 0) ? max_by_q : (CAP_L / items[i].l);
        long long mt = max_by_q;
        if (max_by_m < mt) mt = max_by_m;
        if (max_by_l < mt) mt = max_by_l;
        if (mt < 0) mt = 0;
        items[i].max_take = mt;
    }

    // Build various heuristic orders
    const long double NEG_INF = -1e300L;
    const long double POS_INF = 1e300L;

    vector<long double> ratioApprox(n_items), ratioMass(n_items), ratioVol(n_items), ratioMax(n_items);
    vector<long double> massScore(n_items), volScore(n_items);

    for (int i = 0; i < n_items; i++) {
        if (items[i].max_take == 0) {
            ratioApprox[i] = ratioMass[i] = ratioVol[i] = ratioMax[i] = NEG_INF;
            massScore[i] = volScore[i] = POS_INF;
        } else {
            long double wm = (long double)items[i].m / (long double)CAP_M;
            long double wl = (long double)items[i].l / (long double)CAP_L;
            long double denom = wm + wl;
            if (denom <= 0) denom = 1e-18L;
            ratioApprox[i] = (long double)items[i].v / denom;
            ratioMass[i] = (long double)items[i].v / (long double)items[i].m;
            ratioVol[i]  = (long double)items[i].v / (long double)items[i].l;
            long double maxCost = max(wm, wl);
            if (maxCost <= 0) maxCost = 1e-18L;
            ratioMax[i] = (long double)items[i].v / maxCost;
            massScore[i] = (long double)items[i].m;
            volScore[i] = (long double)items[i].l;
        }
    }

    vector<vector<int>> orders;
    orders.push_back(create_order_from_scores(ratioApprox, true));
    orders.push_back(create_order_from_scores(ratioMass, true));
    orders.push_back(create_order_from_scores(ratioVol, true));
    orders.push_back(create_order_from_scores(ratioMax, true));
    orders.push_back(create_order_from_scores(massScore, false)); // light items first
    orders.push_back(create_order_from_scores(volScore, false));  // small volume first

    mt19937_64 rng(123456);
    uniform_real_distribution<long double> dist(0.8L, 1.2L);

    for (int t = 0; t < 5; t++) {
        vector<long double> noisy(n_items);
        for (int i = 0; i < n_items; i++) {
            if (items[i].max_take == 0) noisy[i] = NEG_INF;
            else noisy[i] = ratioApprox[i] * dist(rng);
        }
        orders.push_back(create_order_from_scores(noisy, true));
    }

    vector<int> refill_order = orders.front(); // use approximate ratio as refill order

    vector<long long> bestX(n_items, 0);
    long long bestVal = 0;

    clock_t t0 = clock();

    for (auto &order : orders) {
        double elapsed = double(clock() - t0) / CLOCKS_PER_SEC;
        if (elapsed > 0.95) break;

        vector<long long> x(n_items, 0);
        long long massUsed = 0, volUsed = 0;
        long long val = greedy_fill(order, x, massUsed, volUsed);
        if (val > bestVal) {
            bestVal = val;
            bestX = x;
        }

        local_search(x, val, massUsed, volUsed, refill_order, t0);
        if (val > bestVal) {
            bestVal = val;
            bestX = x;
        }
    }

    // Output JSON with original keys
    cout << "{\n";
    for (int i = 0; i < n_items; i++) {
        cout << " \"" << items[i].name << "\": " << bestX[i];
        if (i + 1 < n_items) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";

    return 0;
}