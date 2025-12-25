#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire input
    string s((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    size_t pos = 0;

    auto skipWS = [&]() {
        while (pos < s.size() && isspace((unsigned char)s[pos])) ++pos;
    };

    auto parseString = [&]() -> string {
        skipWS();
        if (pos >= s.size() || s[pos] != '"') return "";
        ++pos;
        size_t start = pos;
        while (pos < s.size() && s[pos] != '"') ++pos;
        string res = s.substr(start, pos - start);
        if (pos < s.size() && s[pos] == '"') ++pos;
        return res;
    };

    auto parseLongLong = [&]() -> long long {
        skipWS();
        int sign = 1;
        if (pos < s.size() && s[pos] == '-') {
            sign = -1;
            ++pos;
        }
        long long val = 0;
        while (pos < s.size() && isdigit((unsigned char)s[pos])) {
            val = val * 10 + (s[pos] - '0');
            ++pos;
        }
        return sign * val;
    };

    skipWS();
    if (pos < s.size() && s[pos] == '{') ++pos;

    vector<string> names;
    vector<long long> q, v, m, l;

    while (true) {
        skipWS();
        if (pos >= s.size()) break;
        if (s[pos] == '}') {
            ++pos;
            break;
        }

        string name = parseString();
        if (name.empty()) break;

        // Skip until '['
        while (pos < s.size() && s[pos] != '[') ++pos;
        if (pos < s.size() && s[pos] == '[') ++pos;

        long long nums[4];
        for (int i = 0; i < 4; ++i) {
            nums[i] = parseLongLong();
            skipWS();
            if (i < 3 && pos < s.size() && s[pos] == ',') ++pos;
        }

        // Skip until ']'
        while (pos < s.size() && s[pos] != ']') ++pos;
        if (pos < s.size() && s[pos] == ']') ++pos;

        skipWS();
        if (pos < s.size() && s[pos] == ',') ++pos;

        names.push_back(name);
        q.push_back(nums[0]);
        v.push_back(nums[1]);
        m.push_back(nums[2]);
        l.push_back(nums[3]);
    }

    int n = (int)names.size();
    if (n == 0) {
        cout << "{}\n";
        return 0;
    }

    const long long M_CAP = 20'000'000LL;
    const long long L_CAP = 25'000'000LL;

    vector<long long> bestX(n, 0);
    long long bestVal = 0;

    auto greedyFromOrder = [&](const vector<int> &order) {
        vector<long long> x(n, 0);
        long long usedM = 0;
        long long usedL = 0;
        long long totalVal = 0;
        for (int idx : order) {
            if (usedM >= M_CAP || usedL >= L_CAP) break;
            long long remM = M_CAP - usedM;
            long long remL = L_CAP - usedL;
            long long maxByM = remM / m[idx];
            long long maxByL = remL / l[idx];
            long long canTake = std::min<long long>({q[idx], maxByM, maxByL});
            if (canTake <= 0) continue;
            x[idx] = canTake;
            usedM += canTake * m[idx];
            usedL += canTake * l[idx];
            totalVal += canTake * v[idx];
        }
        if (totalVal > bestVal) {
            bestVal = totalVal;
            bestX = std::move(x);
        }
    };

    double M_cap_d = (double)M_CAP;
    double L_cap_d = (double)L_CAP;
    vector<double> mNorm(n), lNorm(n);
    for (int i = 0; i < n; ++i) {
        mNorm[i] = (double)m[i] / M_cap_d;
        lNorm[i] = (double)l[i] / L_cap_d;
    }

    auto runHeuristic = [&](auto getDensity) {
        struct Pair {
            double d;
            int idx;
        };
        vector<Pair> arr;
        arr.reserve(n);
        for (int i = 0; i < n; ++i) {
            double d = getDensity(i);
            if (!std::isfinite(d)) d = -1e300;
            arr.push_back({d, i});
        }
        sort(arr.begin(), arr.end(), [](const Pair &a, const Pair &b) {
            return a.d > b.d;
        });
        vector<int> order;
        order.reserve(n);
        for (auto &p : arr) order.push_back(p.idx);
        greedyFromOrder(order);
    };

    // Basic heuristics
    runHeuristic([&](int i) { return (double)v[i] / (double)m[i]; });                     // value per mass
    runHeuristic([&](int i) { return (double)v[i] / (double)l[i]; });                     // value per volume
    runHeuristic([&](int i) { return (double)v[i]; });                                     // raw value
    runHeuristic([&](int i) { return (double)v[i] / (mNorm[i] + lNorm[i]); });             // value per combined normalized size
    runHeuristic([&](int i) { return (double)v[i] / std::max(mNorm[i], lNorm[i]); });      // value per max normalized
    runHeuristic([&](int i) {
        double s = mNorm[i] * mNorm[i] + lNorm[i] * lNorm[i];
        return (double)v[i] / s;
    });
    runHeuristic([&](int i) { return 1.0 / (mNorm[i] + lNorm[i]); });                      // prioritize small items

    // Directional heuristics
    const int K_dir = 32;
    const double PI = acos(-1.0);
    for (int k = 0; k <= K_dir; ++k) {
        double theta = (PI / 2.0) * k / (double)K_dir;
        double alpha = cos(theta);
        double beta = sin(theta);
        runHeuristic([&](int i) {
            double cons = alpha * mNorm[i] + beta * lNorm[i];
            return (double)v[i] / cons;
        });
    }

    // Local search improvement
    long long usedM = 0, usedL = 0;
    for (int i = 0; i < n; ++i) {
        usedM += bestX[i] * m[i];
        usedL += bestX[i] * l[i];
    }

    auto tryExchangeType = [&](int addIdx, vector<long long> &x, long long &curUsedM,
                               long long &curUsedL, long long &curVal) -> bool {
        if (x[addIdx] >= q[addIdx]) return false;

        long long M_rem = M_CAP - curUsedM;
        long long L_rem = L_CAP - curUsedL;

        if (m[addIdx] <= M_rem && l[addIdx] <= L_rem) {
            x[addIdx] += 1;
            curUsedM += m[addIdx];
            curUsedL += l[addIdx];
            curVal += v[addIdx];
            return true;
        }

        long long mass_needed = std::max(0LL, m[addIdx] - M_rem);
        long long vol_needed = std::max(0LL, l[addIdx] - L_rem);
        long long w_m = mass_needed;
        long long w_l = vol_needed;

        if (w_m == 0 && w_l == 0) {
            x[addIdx] += 1;
            curUsedM += m[addIdx];
            curUsedL += l[addIdx];
            curVal += v[addIdx];
            return true;
        }

        vector<int> cand;
        cand.reserve(n);
        for (int i = 0; i < n; ++i) {
            if (i == addIdx) continue;
            if (x[i] > 0) cand.push_back(i);
        }
        if (cand.empty()) return false;

        struct Node {
            double score;
            int idx;
        };
        vector<Node> nodes;
        nodes.reserve(cand.size());
        for (int i : cand) {
            long long denom_ll = w_m * m[i] + w_l * l[i];
            double denom = (double)denom_ll;
            double score;
            if (denom <= 0.0) score = 1e300;
            else score = (double)v[i] / denom;
            nodes.push_back({score, i});
        }
        sort(nodes.begin(), nodes.end(), [](const Node &a, const Node &b) {
            return a.score < b.score;  // remove lowest score first
        });

        vector<long long> removeCnt(n, 0);
        long long freedM = 0, freedL = 0, valueLoss = 0;
        for (const auto &nd : nodes) {
            if (freedM >= mass_needed && freedL >= vol_needed) break;
            int i = nd.idx;
            long long available = x[i] - removeCnt[i];
            if (available <= 0) continue;

            long long remMassNeed = std::max(0LL, mass_needed - freedM);
            long long remVolNeed = std::max(0LL, vol_needed - freedL);
            if (remMassNeed <= 0 && remVolNeed <= 0) break;

            long long unitsByM = remMassNeed > 0 ? ((remMassNeed + m[i] - 1) / m[i]) : 0;
            long long unitsByL = remVolNeed > 0 ? ((remVolNeed + l[i] - 1) / l[i]) : 0;
            long long unitsNeed = std::max(unitsByM, unitsByL);
            if (unitsNeed <= 0) unitsNeed = 1;
            if (unitsNeed > available) unitsNeed = available;

            freedM += unitsNeed * m[i];
            freedL += unitsNeed * l[i];
            valueLoss += unitsNeed * v[i];
            removeCnt[i] += unitsNeed;
        }

        if (freedM < mass_needed || freedL < vol_needed) return false;

        long long netGain = v[addIdx] - valueLoss;
        if (netGain <= 0) return false;

        // Commit changes
        x[addIdx] += 1;
        curUsedM += m[addIdx];
        curUsedL += l[addIdx];
        curVal += v[addIdx];
        for (int i = 0; i < n; ++i) {
            long long c = removeCnt[i];
            if (c > 0) {
                x[i] -= c;
                curUsedM -= c * m[i];
                curUsedL -= c * l[i];
                curVal -= c * v[i];
            }
        }
        return true;
    };

    const int MAX_IMPROVE_STEPS = 2000;
    int improveCount = 0;
    bool improved = true;
    while (improved && improveCount < MAX_IMPROVE_STEPS) {
        improved = false;
        for (int j = 0; j < n && improveCount < MAX_IMPROVE_STEPS; ++j) {
            if (tryExchangeType(j, bestX, usedM, usedL, bestVal)) {
                improved = true;
                ++improveCount;
            }
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