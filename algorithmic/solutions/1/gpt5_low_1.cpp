#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    long long q;
    long long v;
    long long m;
    long long l;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // Read entire stdin into a string
    string input, line;
    while (getline(cin, line)) {
        input += line;
        input += '\n';
    }
    // Regex to parse: "name": [ q, v, m, l ]
    // Names are lowercase ASCII letters (as per statement)
    regex re("\"([a-z]+)\"\\s*:\\s*\\[\\s*(\\d+)\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)\\s*\\]");
    sregex_iterator it(input.begin(), input.end(), re);
    sregex_iterator end;

    vector<Item> items;
    for (; it != end; ++it) {
        smatch mth = *it;
        Item itx;
        itx.name = mth[1].str();
        itx.q = stoll(mth[2].str());
        itx.v = stoll(mth[3].str());
        itx.m = stoll(mth[4].str());
        itx.l = stoll(mth[5].str());
        items.push_back(itx);
    }
    int n = (int)items.size();
    if (n == 0) {
        // If parsing failed, output empty JSON
        cout << "{\n}\n";
        return 0;
    }

    const long long M_CAP = 20000000LL;
    const long long L_CAP = 25000000LL;

    auto greedy_fill = [&](double alpha) {
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);
        vector<double> cost(n), density(n);
        for (int i = 0; i < n; ++i) {
            double cm = (double)items[i].m / (double)M_CAP;
            double cl = (double)items[i].l / (double)L_CAP;
            cost[i] = alpha * cm + (1.0 - alpha) * cl;
            if (cost[i] <= 0) cost[i] = 1e-18;
            density[i] = (double)items[i].v / cost[i];
        }
        sort(idx.begin(), idx.end(), [&](int a, int b){
            if (density[a] != density[b]) return density[a] > density[b];
            return items[a].v > items[b].v;
        });
        vector<long long> take(n, 0);
        long long usedM = 0, usedL = 0;
        for (int id : idx) {
            if (items[id].m > M_CAP || items[id].l > L_CAP) continue;
            long long capM = (items[id].m == 0 ? items[id].q : (M_CAP - usedM) / items[id].m);
            long long capL = (items[id].l == 0 ? items[id].q : (L_CAP - usedL) / items[id].l);
            long long t = min({items[id].q, capM, capL});
            if (t > 0) {
                take[id] = t;
                usedM += t * items[id].m;
                usedL += t * items[id].l;
            }
        }
        return take;
    };

    auto value_of = [&](const vector<long long>& take){
        __int128 sum = 0;
        for (int i = 0; i < n; ++i) sum += (__int128)take[i] * items[i].v;
        return sum;
    };
    auto mass_of = [&](const vector<long long>& take){
        __int128 sum = 0;
        for (int i = 0; i < n; ++i) sum += (__int128)take[i] * items[i].m;
        return sum;
    };
    auto vol_of = [&](const vector<long long>& take){
        __int128 sum = 0;
        for (int i = 0; i < n; ++i) sum += (__int128)take[i] * items[i].l;
        return sum;
    };

    vector<long long> best_take(n, 0);
    __int128 best_val = -1;
    double best_alpha = 0.5;

    // Try multiple alphas
    vector<double> alphas;
    for (int i = 0; i <= 10; ++i) alphas.push_back(i / 10.0);
    alphas.push_back(0.33);
    alphas.push_back(0.67);

    for (double a : alphas) {
        auto take = greedy_fill(a);
        __int128 v = value_of(take);
        if (v > best_val) {
            best_val = v;
            best_take = take;
            best_alpha = a;
        }
    }

    // Local improvement
    auto improve = [&](vector<long long>& take, double alpha){
        long long totM = (long long)mass_of(take);
        long long totL = (long long)vol_of(take);
        long long totV = 0;
        for (int i = 0; i < n; ++i) totV += take[i] * items[i].v;

        vector<double> cost(n), dens(n);
        for (int i = 0; i < n; ++i) {
            double cm = (double)items[i].m / (double)M_CAP;
            double cl = (double)items[i].l / (double)L_CAP;
            cost[i] = alpha * cm + (1.0 - alpha) * cl;
            if (cost[i] <= 0) cost[i] = 1e-18;
            dens[i] = (double)items[i].v / cost[i];
        }
        vector<int> asc(n);
        iota(asc.begin(), asc.end(), 0);
        sort(asc.begin(), asc.end(), [&](int a, int b){
            if (dens[a] != dens[b]) return dens[a] < dens[b];
            return items[a].v < items[b].v;
        });

        bool improved = true;
        int passes = 0;
        while (improved && passes < 3) {
            improved = false;
            ++passes;
            for (int t = 0; t < n; ++t) {
                if (take[t] >= items[t].q) continue;
                long long needM = max(0LL, totM + items[t].m - M_CAP);
                long long needL = max(0LL, totL + items[t].l - L_CAP);
                if (needM <= 0 && needL <= 0) {
                    // Can add directly
                    take[t] += 1;
                    totM += items[t].m;
                    totL += items[t].l;
                    totV += items[t].v;
                    improved = true;
                    continue;
                }
                vector<long long> removed(n, 0);
                long long remM = 0, remL = 0;
                long long remV = 0;
                for (int j : asc) {
                    if (j == t) continue; // do not remove from the same type for stability
                    if (take[j] == 0) continue;
                    if (remM >= needM && remL >= needL) break;
                    long long defM = max(0LL, needM - remM);
                    long long defL = max(0LL, needL - remL);
                    long long xM = (defM == 0 ? 0 : (defM + items[j].m - 1) / items[j].m);
                    long long xL = (defL == 0 ? 0 : (defL + items[j].l - 1) / items[j].l);
                    long long x = max(xM, xL);
                    if (x <= 0) x = 1;
                    x = min(x, take[j]);
                    if (x <= 0) continue;
                    removed[j] += x;
                    remM += x * items[j].m;
                    remL += x * items[j].l;
                    remV += x * items[j].v;
                }
                if (remM >= needM && remL >= needL) {
                    long long deltaV = items[t].v - remV;
                    if (deltaV > 0) {
                        take[t] += 1;
                        for (int j = 0; j < n; ++j) {
                            if (removed[j] > 0) take[j] -= removed[j];
                        }
                        totM += items[t].m - remM;
                        totL += items[t].l - remL;
                        totV += deltaV;
                        improved = true;
                    }
                }
            }
        }
        return;
    };

    improve(best_take, best_alpha);

    // Ensure feasibility just in case
    auto ensure_feasible = [&](vector<long long>& take){
        long long usedM = 0, usedL = 0;
        for (int i = 0; i < n; ++i) {
            usedM += take[i] * items[i].m;
            usedL += take[i] * items[i].l;
        }
        if (usedM <= M_CAP && usedL <= L_CAP) return;
        // Remove worst density items until feasible
        vector<double> dens(n);
        for (int i = 0; i < n; ++i) {
            double cm = (double)items[i].m / (double)M_CAP;
            double cl = (double)items[i].l / (double)L_CAP;
            double cost = 0.5 * cm + 0.5 * cl;
            if (cost <= 0) cost = 1e-18;
            dens[i] = (double)items[i].v / cost;
        }
        vector<int> asc(n);
        iota(asc.begin(), asc.end(), 0);
        sort(asc.begin(), asc.end(), [&](int a, int b){
            if (dens[a] != dens[b]) return dens[a] < dens[b];
            return items[a].v < items[b].v;
        });
        for (int j : asc) {
            while ((usedM > M_CAP || usedL > L_CAP) && take[j] > 0) {
                take[j]--;
                usedM -= items[j].m;
                usedL -= items[j].l;
            }
            if (usedM <= M_CAP && usedL <= L_CAP) break;
        }
    };
    ensure_feasible(best_take);

    // Output JSON with same keys order
    cout << "{\n";
    for (int i = 0; i < n; ++i) {
        cout << " \"" << items[i].name << "\": " << best_take[i];
        if (i + 1 < n) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";
    return 0;
}