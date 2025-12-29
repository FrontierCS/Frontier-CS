#include <bits/stdc++.h>
using namespace std;

// Capacities in mg and µL
const long long MASS_CAP = 20LL * 1000000LL;
const long long VOL_CAP  = 25LL * 1000000LL;

// Global item data
vector<string> names;
vector<int> qty;
vector<long long> val, massv, volv;

// JSON parsing globals
string json_input;
size_t pos_json = 0;

void skip_ws() {
    while (pos_json < json_input.size() &&
           isspace((unsigned char)json_input[pos_json])) {
        ++pos_json;
    }
}

string parse_string() {
    skip_ws();
    if (pos_json >= json_input.size() || json_input[pos_json] != '"') return "";
    ++pos_json; // skip opening quote
    string res;
    while (pos_json < json_input.size() && json_input[pos_json] != '"') {
        res.push_back(json_input[pos_json++]);
    }
    if (pos_json < json_input.size() && json_input[pos_json] == '"') ++pos_json;
    return res;
}

long long parse_ll() {
    skip_ws();
    int sign = 1;
    if (pos_json < json_input.size() && json_input[pos_json] == '-') {
        sign = -1;
        ++pos_json;
    }
    long long v = 0;
    while (pos_json < json_input.size() &&
           isdigit((unsigned char)json_input[pos_json])) {
        v = v * 10 + (json_input[pos_json] - '0');
        ++pos_json;
    }
    return sign * v;
}

void build_greedy(int heurType, vector<int> &x) {
    int n = (int)names.size();
    x.assign(n, 0);
    vector<double> ratio(n);

    for (int i = 0; i < n; ++i) {
        double cost = 0.0;
        double m = (double)massv[i];
        double l = (double)volv[i];
        double nm = m / (double)MASS_CAP;
        double nl = l / (double)VOL_CAP;
        switch (heurType) {
            case 0: // value per mass
                cost = m;
                break;
            case 1: // value per volume
                cost = l;
                break;
            case 2: // equal normalized
                cost = nm + nl;
                break;
            case 3: // bias mass
                cost = 0.7 * nm + 0.3 * nl;
                break;
            case 4: // bias volume
                cost = 0.3 * nm + 0.7 * nl;
                break;
            case 5: // max normalized
                cost = max(nm, nl);
                break;
            case 6: { // L2 squared
                cost = nm * nm + nl * nl;
                break;
            }
            default:
                cost = nm + nl;
                break;
        }
        if (cost <= 0.0) cost = 1e-9;
        ratio[i] = (double)val[i] / cost;
    }

    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (ratio[a] == ratio[b]) {
            long long ca = massv[a] + volv[a];
            long long cb = massv[b] + volv[b];
            if (ca != cb) return ca < cb;
            return a < b;
        }
        return ratio[a] > ratio[b];
    });

    long long Mrem = MASS_CAP;
    long long Lrem = VOL_CAP;

    for (int idx : order) {
        if (Mrem <= 0 || Lrem <= 0) break;
        if (massv[idx] <= 0 || volv[idx] <= 0) continue;
        long long maxK1 = qty[idx];
        long long maxK2 = Mrem / massv[idx];
        long long maxK3 = Lrem / volv[idx];
        long long k = min(maxK1, min(maxK2, maxK3));
        if (k <= 0) continue;
        x[idx] += (int)k;
        Mrem -= k * massv[idx];
        Lrem -= k * volv[idx];
    }
}

long long improve(vector<int> &x) {
    int n = (int)names.size();
    long long Mcur = 0, Lcur = 0, Vcur = 0;
    for (int i = 0; i < n; ++i) {
        Mcur += (long long)x[i] * massv[i];
        Lcur += (long long)x[i] * volv[i];
        Vcur += (long long)x[i] * val[i];
    }

    auto fill_capacity = [&]() {
        while (true) {
            long long Mfree = MASS_CAP - Mcur;
            long long Lfree = VOL_CAP - Lcur;
            if (Mfree <= 0 || Lfree <= 0) break;
            long long bestGain = 0;
            int bestJ = -1;
            long long bestK = 0;
            for (int j = 0; j < n; ++j) {
                if (x[j] >= qty[j]) continue;
                if (massv[j] > Mfree || volv[j] > Lfree) continue;
                long long maxK1 = (long long)qty[j] - x[j];
                long long maxK2 = Mfree / massv[j];
                long long maxK3 = Lfree / volv[j];
                long long k = min(maxK1, min(maxK2, maxK3));
                if (k <= 0) continue;
                long long gain = k * val[j];
                if (gain > bestGain) {
                    bestGain = gain;
                    bestJ = j;
                    bestK = k;
                }
            }
            if (bestJ == -1) break;
            x[bestJ] += (int)bestK;
            Mcur += bestK * massv[bestJ];
            Lcur += bestK * volv[bestJ];
            Vcur += bestGain;
        }
    };

    fill_capacity();

    const int MAX_ITERS = 60;
    for (int iter = 0; iter < MAX_ITERS; ++iter) {
        long long bestDV = 0;
        int moveType = 0; // 0 none, 1 one-drop, 2 two-drop
        int bi1 = -1, bi2 = -1, bj = -1;
        long long bk = 0;

        // One-drop moves: remove 1 of i, add k of j
        for (int i = 0; i < n; ++i) {
            if (x[i] <= 0) continue;
            for (int j = 0; j < n; ++j) {
                if (j == i) continue;
                if (x[j] >= qty[j]) continue;
                long long Mfree = MASS_CAP - (Mcur - massv[i]);
                long long Lfree = VOL_CAP - (Lcur - volv[i]);
                if (Mfree <= 0 || Lfree <= 0) continue;
                if (massv[j] > Mfree || volv[j] > Lfree) continue;
                long long maxK1 = (long long)qty[j] - x[j];
                long long maxK2 = Mfree / massv[j];
                long long maxK3 = Lfree / volv[j];
                long long k = min(maxK1, min(maxK2, maxK3));
                if (k <= 0) continue;
                long long DV = -val[i] + k * val[j];
                if (DV > bestDV) {
                    bestDV = DV;
                    moveType = 1;
                    bi1 = i;
                    bj = j;
                    bk = k;
                }
            }
        }

        // Two-drop moves: remove 2 items (a,b), add k of j
        for (int a = 0; a < n; ++a) {
            if (x[a] <= 0) continue;
            for (int b = a; b < n; ++b) {
                if (b == a) {
                    if (x[a] < 2) continue;
                } else {
                    if (x[b] <= 0) continue;
                }
                long long removeMass = massv[a] + (b == a ? massv[a] : massv[b]);
                long long removeVol  = volv[a] + (b == a ? volv[a] : volv[b]);
                long long McurP = Mcur - removeMass;
                long long LcurP = Lcur - removeVol;
                if (McurP < 0 || LcurP < 0) continue;
                long long Mfree = MASS_CAP - McurP;
                long long Lfree = VOL_CAP - LcurP;
                if (Mfree <= 0 || Lfree <= 0) continue;

                for (int j = 0; j < n; ++j) {
                    if (j == a || j == b) continue;
                    if (x[j] >= qty[j]) continue;
                    if (massv[j] > Mfree || volv[j] > Lfree) continue;
                    long long maxK1 = (long long)qty[j] - x[j];
                    long long maxK2 = Mfree / massv[j];
                    long long maxK3 = Lfree / volv[j];
                    long long k = min(maxK1, min(maxK2, maxK3));
                    if (k <= 0) continue;
                    long long DV = -val[a] - (b == a ? val[a] : val[b]) + k * val[j];
                    if (DV > bestDV) {
                        bestDV = DV;
                        moveType = 2;
                        bi1 = a;
                        bi2 = b;
                        bj = j;
                        bk = k;
                    }
                }
            }
        }

        if (bestDV <= 0 || moveType == 0) break;

        if (moveType == 1) {
            x[bi1]--;
            x[bj] += (int)bk;
            Mcur = Mcur - massv[bi1] + bk * massv[bj];
            Lcur = Lcur - volv[bi1] + bk * volv[bj];
        } else { // moveType == 2
            x[bi1]--;
            x[bi2]--;
            x[bj] += (int)bk;
            long long removeMass = massv[bi1] + (bi2 == bi1 ? massv[bi1] : massv[bi2]);
            long long removeVol  = volv[bi1] + (bi2 == bi1 ? volv[bi1] : volv[bi2]);
            Mcur = Mcur - removeMass + bk * massv[bj];
            Lcur = Lcur - removeVol  + bk * volv[bj];
        }
        Vcur += bestDV;

        fill_capacity();
    }

    return Vcur;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    json_input.assign(istreambuf_iterator<char>(cin), istreambuf_iterator<char>());
    pos_json = 0;

    skip_ws();
    if (pos_json < json_input.size() && json_input[pos_json] == '{') ++pos_json;

    names.clear();
    qty.clear();
    val.clear();
    massv.clear();
    volv.clear();

    while (true) {
        skip_ws();
        if (pos_json >= json_input.size()) break;
        if (json_input[pos_json] == '}') {
            ++pos_json;
            break;
        }

        string key = parse_string();
        skip_ws();
        if (pos_json < json_input.size() && json_input[pos_json] == ':') ++pos_json;
        skip_ws();
        if (pos_json < json_input.size() && json_input[pos_json] == '[') ++pos_json;

        long long qv = parse_ll();
        skip_ws();
        if (pos_json < json_input.size() && json_input[pos_json] == ',') ++pos_json;
        long long vv = parse_ll();
        skip_ws();
        if (pos_json < json_input.size() && json_input[pos_json] == ',') ++pos_json;
        long long mv = parse_ll();
        skip_ws();
        if (pos_json < json_input.size() && json_input[pos_json] == ',') ++pos_json;
        long long lv = parse_ll();
        skip_ws();
        if (pos_json < json_input.size() && json_input[pos_json] == ']') ++pos_json;

        names.push_back(key);
        qty.push_back((int)qv);
        val.push_back(vv);
        massv.push_back(mv);
        volv.push_back(lv);

        skip_ws();
        if (pos_json < json_input.size() && json_input[pos_json] == ',') {
            ++pos_json;
            continue;
        }
    }

    int n = (int)names.size();
    vector<int> bestX(n, 0);
    long long bestValue = -1;

    // Heuristic greedy starts
    for (int ht = 0; ht < 7; ++ht) {
        vector<int> x(n, 0);
        build_greedy(ht, x);
        long long vsol = improve(x);
        if (vsol > bestValue) {
            bestValue = vsol;
            bestX = x;
        }
    }

    // Start from empty as additional candidate
    {
        vector<int> x(n, 0);
        long long vsol = improve(x);
        if (vsol > bestValue) {
            bestValue = vsol;
            bestX = x;
        }
    }

    // Output JSON
    cout << "{\n";
    for (int i = 0; i < n; ++i) {
        cout << " \"" << names[i] << "\": " << bestX[i];
        if (i + 1 < n) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";

    return 0;
}