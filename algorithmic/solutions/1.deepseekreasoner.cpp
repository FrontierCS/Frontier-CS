#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <random>
#include <cctype>
#include <cmath>

using namespace std;

const long long M = 20000000;   // mg
const long long L = 25000000;   // µL

struct Treasure {
    string name;
    long long q; // max quantity
    long long v; // value per item
    long long m; // mass per item (mg)
    long long l; // volume per item (µL)
    double density;
};

vector<Treasure> treasures;

void parseInput() {
    string s;
    char c;
    while (cin.get(c)) s += c;

    size_t i = 0;
    auto skipWS = [&]() {
        while (i < s.size() && isspace(s[i])) i++;
    };

    skipWS();
    if (s[i] != '{') return;
    i++;
    while (true) {
        skipWS();
        if (s[i] == '}') break;
        if (s[i] == '"') {
            i++;
            size_t start = i;
            while (s[i] != '"') i++;
            string key = s.substr(start, i - start);
            i++; // skip '"'
            skipWS();
            if (s[i] != ':') return;
            i++;
            skipWS();
            if (s[i] != '[') return;
            i++;
            vector<long long> nums;
            for (int j = 0; j < 4; j++) {
                skipWS();
                long long num = 0;
                while (i < s.size() && isdigit(s[i])) {
                    num = num * 10 + (s[i] - '0');
                    i++;
                }
                nums.push_back(num);
                if (j < 3) {
                    skipWS();
                    if (s[i] != ',') return;
                    i++;
                }
            }
            skipWS();
            if (s[i] != ']') return;
            i++;
            treasures.push_back({key, nums[0], nums[1], nums[2], nums[3], 0.0});
            skipWS();
            if (s[i] == ',') i++;
            else if (s[i] == '}') break;
            else return;
        }
    }
}

vector<long long> greedy(const vector<int>& order) {
    vector<long long> cnt(treasures.size(), 0);
    long long cur_m = 0, cur_l = 0;
    for (int idx : order) {
        const Treasure& t = treasures[idx];
        long long maxTake = t.q;
        if (t.m > 0) maxTake = min(maxTake, (M - cur_m) / t.m);
        if (t.l > 0) maxTake = min(maxTake, (L - cur_l) / t.l);
        cnt[idx] = maxTake;
        cur_m += maxTake * t.m;
        cur_l += maxTake * t.l;
    }
    return cnt;
}

void improve(vector<long long>& cnt, long long& cur_m, long long& cur_l, long long& cur_v) {
    bool improved = true;
    while (improved) {
        improved = false;
        // try to add one item
        for (int i = 0; i < (int)treasures.size(); i++) {
            if (cnt[i] < treasures[i].q) {
                long long new_m = cur_m + treasures[i].m;
                long long new_l = cur_l + treasures[i].l;
                if (new_m <= M && new_l <= L) {
                    cnt[i]++;
                    cur_m = new_m;
                    cur_l = new_l;
                    cur_v += treasures[i].v;
                    improved = true;
                }
            }
        }
        // try to swap: remove one from j, add one to i
        for (int i = 0; i < (int)treasures.size() && !improved; i++) {
            for (int j = 0; j < (int)treasures.size(); j++) {
                if (i == j) continue;
                if (cnt[i] < treasures[i].q && cnt[j] > 0) {
                    long long delta_m = treasures[i].m - treasures[j].m;
                    long long delta_l = treasures[i].l - treasures[j].l;
                    long long delta_v = treasures[i].v - treasures[j].v;
                    if (delta_v > 0 && cur_m + delta_m <= M && cur_l + delta_l <= L) {
                        cnt[i]++; cnt[j]--;
                        cur_m += delta_m;
                        cur_l += delta_l;
                        cur_v += delta_v;
                        improved = true;
                        break;
                    }
                }
            }
            if (improved) break;
        }
    }
}

void finalRefine(vector<long long>& cnt, long long& cur_m, long long& cur_l, long long& cur_v) {
    int n = treasures.size();
    for (int i = 0; i < n; i++) {
        for (int j = i+1; j < n; j++) {
            long long cur_xi = cnt[i], cur_xj = cnt[j];
            long long base_m = cur_m - cur_xi*treasures[i].m - cur_xj*treasures[j].m;
            long long base_l = cur_l - cur_xi*treasures[i].l - cur_xj*treasures[j].l;
            long long base_v = cur_v - cur_xi*treasures[i].v - cur_xj*treasures[j].v;
            long long best_xi = cur_xi, best_xj = cur_xj;
            long long best_m = cur_m, best_l = cur_l, best_v = cur_v;
            for (long long xi = max(0LL, cur_xi-10); xi <= min(treasures[i].q, cur_xi+10); xi++) {
                for (long long xj = max(0LL, cur_xj-10); xj <= min(treasures[j].q, cur_xj+10); xj++) {
                    long long new_m = base_m + xi*treasures[i].m + xj*treasures[j].m;
                    long long new_l = base_l + xi*treasures[i].l + xj*treasures[j].l;
                    if (new_m <= M && new_l <= L) {
                        long long new_v = base_v + xi*treasures[i].v + xj*treasures[j].v;
                        if (new_v > best_v) {
                            best_v = new_v;
                            best_m = new_m;
                            best_l = new_l;
                            best_xi = xi;
                            best_xj = xj;
                        }
                    }
                }
            }
            if (best_xi != cur_xi || best_xj != cur_xj) {
                cnt[i] = best_xi;
                cnt[j] = best_xj;
                cur_m = best_m;
                cur_l = best_l;
                cur_v = best_v;
            }
        }
    }
}

int main() {
    parseInput();
    int n = treasures.size();
    // compute density: value per combined resource
    for (int i = 0; i < n; i++) {
        // density = v_i / (m_i/M + l_i/L) = v_i * M * L / (m_i * L + l_i * M)
        double denom = treasures[i].m * L + treasures[i].l * M;
        treasures[i].density = (denom > 0) ? (treasures[i].v * M * L / denom) : 1e18;
    }

    vector<int> order(n);
    for (int i = 0; i < n; i++) order[i] = i;
    sort(order.begin(), order.end(), [&](int a, int b) {
        return treasures[a].density > treasures[b].density;
    });

    // initial solution from density order
    vector<long long> best_cnt = greedy(order);
    long long best_m = 0, best_l = 0, best_v = 0;
    for (int i = 0; i < n; i++) {
        best_m += best_cnt[i] * treasures[i].m;
        best_l += best_cnt[i] * treasures[i].l;
        best_v += best_cnt[i] * treasures[i].v;
    }
    improve(best_cnt, best_m, best_l, best_v);

    // random permutations
    mt19937 rng(123456); // fixed seed for reproducibility
    for (int iter = 0; iter < 100; iter++) {
        shuffle(order.begin(), order.end(), rng);
        vector<long long> cnt = greedy(order);
        long long cur_m = 0, cur_l = 0, cur_v = 0;
        for (int i = 0; i < n; i++) {
            cur_m += cnt[i] * treasures[i].m;
            cur_l += cnt[i] * treasures[i].l;
            cur_v += cnt[i] * treasures[i].v;
        }
        improve(cnt, cur_m, cur_l, cur_v);
        if (cur_v > best_v) {
            best_v = cur_v;
            best_m = cur_m;
            best_l = cur_l;
            best_cnt = cnt;
        }
    }

    // final refinement on pairs
    finalRefine(best_cnt, best_m, best_l, best_v);

    // output JSON
    cout << "{\n";
    for (int i = 0; i < n; i++) {
        cout << " \"" << treasures[i].name << "\": " << best_cnt[i];
        if (i != n-1) cout << ",";
        cout << "\n";
    }
    cout << "}\n";

    return 0;
}