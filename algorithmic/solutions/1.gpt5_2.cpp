#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct Category {
    string name;
    ll q, v, m, l;
};

struct Chunk {
    int orig;
    ll take;
    int wm, wl;
    ll value;
};

struct Parser {
    string s;
    size_t pos = 0;
    Parser(const string& str) : s(str), pos(0) {}
    void skipWS() {
        while (pos < s.size() && isspace((unsigned char)s[pos])) pos++;
    }
    bool nextChar(char c) {
        skipWS();
        if (pos < s.size() && s[pos] == c) { pos++; return true; }
        return false;
    }
    string nextString() {
        // find next quote
        while (pos < s.size() && s[pos] != '"') pos++;
        if (pos >= s.size()) return "";
        pos++; // skip initial "
        string res;
        while (pos < s.size()) {
            char ch = s[pos++];
            if (ch == '\\') {
                if (pos < s.size()) {
                    char esc = s[pos++];
                    // handle only simple escapes
                    if (esc == '"' || esc == '\\' || esc == '/') res.push_back(esc);
                    else if (esc == 'b') res.push_back('\b');
                    else if (esc == 'f') res.push_back('\f');
                    else if (esc == 'n') res.push_back('\n');
                    else if (esc == 'r') res.push_back('\r');
                    else if (esc == 't') res.push_back('\t');
                    else res.push_back(esc);
                }
            } else if (ch == '"') {
                break;
            } else {
                res.push_back(ch);
            }
        }
        return res;
    }
    ll nextInt() {
        // move to next '-' or digit
        while (pos < s.size() && !(s[pos] == '-' || (s[pos] >= '0' && s[pos] <= '9'))) pos++;
        bool neg = false;
        if (pos < s.size() && s[pos] == '-') { neg = true; pos++; }
        ll val = 0;
        while (pos < s.size() && s[pos] >= '0' && s[pos] <= '9') {
            val = val * 10 + (s[pos] - '0');
            pos++;
        }
        return neg ? -val : val;
    }
};

static const ll M_CAP = 20000000; // mg
static const ll L_CAP = 25000000; // uL

struct Solution {
    vector<ll> cnt;
    ll value = 0;
    ll msum = 0;
    ll lsum = 0;
};

static inline void computeTotals(const vector<Category>& items, const vector<ll>& cnt, ll& val, ll& msum, ll& lsum) {
    val = 0; msum = 0; lsum = 0;
    int n = (int)items.size();
    for (int i = 0; i < n; ++i) {
        if (cnt[i] <= 0) continue;
        val += cnt[i] * items[i].v;
        msum += cnt[i] * items[i].m;
        lsum += cnt[i] * items[i].l;
    }
}

static inline Solution makeSolution(const vector<Category>& items, const vector<ll>& cnt) {
    Solution s;
    s.cnt = cnt;
    computeTotals(items, cnt, s.value, s.msum, s.lsum);
    return s;
}

static inline vector<ll> greedy_pack(const vector<Category>& items, double t, const vector<ll>& qcap) {
    int n = (int)items.size();
    vector<int> idx(n);
    for (int i = 0; i < n; ++i) idx[i] = i;
    double M = (double)M_CAP, L = (double)L_CAP;
    vector<double> dens(n, 0.0);
    for (int i = 0; i < n; ++i) {
        if (items[i].m > M_CAP || items[i].l > L_CAP) { dens[i] = -1; continue; }
        double denom = t * ((double)items[i].m / M) + (1.0 - t) * ((double)items[i].l / L);
        if (denom <= 0) dens[i] = 0;
        else dens[i] = (double)items[i].v / denom;
    }
    sort(idx.begin(), idx.end(), [&](int a, int b){
        if (dens[a] != dens[b]) return dens[a] > dens[b];
        return items[a].v > items[b].v;
    });
    vector<ll> cnt(n, 0);
    ll remM = M_CAP, remL = L_CAP;
    for (int it : idx) {
        if (items[it].m > remM || items[it].l > remL) continue;
        ll can = min(qcap[it], min(remM / items[it].m, remL / items[it].l));
        if (can <= 0) continue;
        cnt[it] = can;
        remM -= can * items[it].m;
        remL -= can * items[it].l;
    }
    return cnt;
}

static inline void fill_leftover(vector<ll>& cnt, const vector<Category>& items, const vector<ll>& qcap) {
    ll usedM = 0, usedL = 0, val = 0;
    computeTotals(items, cnt, val, usedM, usedL);
    ll remM = M_CAP - usedM;
    ll remL = L_CAP - usedL;
    if (remM <= 0 || remL <= 0) return;
    double normM = (double)remM / (double)M_CAP;
    double normL = (double)remL / (double)L_CAP;
    double t = (normM + normL > 0) ? (normM / (normM + normL)) : 0.5;
    int n = (int)items.size();
    vector<int> idx(n);
    for (int i = 0; i < n; ++i) idx[i] = i;
    double M = (double)M_CAP, L = (double)L_CAP;
    vector<double> dens(n);
    for (int i = 0; i < n; ++i) {
        double denom = t * ((double)items[i].m / M) + (1.0 - t) * ((double)items[i].l / L);
        dens[i] = (denom > 0) ? (double)items[i].v / denom : 0;
    }
    sort(idx.begin(), idx.end(), [&](int a, int b){
        if (dens[a] != dens[b]) return dens[a] > dens[b];
        return items[a].v > items[b].v;
    });
    for (int it : idx) {
        if (items[it].m > remM || items[it].l > remL) continue;
        ll want = qcap[it] - cnt[it];
        if (want <= 0) continue;
        ll can = min(want, min(remM / items[it].m, remL / items[it].l));
        if (can <= 0) continue;
        cnt[it] += can;
        remM -= can * items[it].m;
        remL -= can * items[it].l;
        if (remM <= 0 || remL <= 0) break;
    }
}

static inline vector<ll> dp_solution(const vector<Category>& items, const vector<ll>& qcap) {
    // scaled 2D DP with ceil for item chunks
    const int S_M = 100000; // 0.1 kg
    const int S_L = 100000; // 0.1 L
    const int Tm = (int)(M_CAP / S_M);
    const int Tl = (int)(L_CAP / S_L);
    vector<Chunk> chunks;
    chunks.reserve(256);
    int n = (int)items.size();
    for (int i = 0; i < n; ++i) {
        ll qeff = qcap[i];
        if (qeff <= 0) continue;
        ll k = 1;
        while (qeff > 0) {
            ll take = min(k, qeff);
            // compute scaled weights per chunk with ceil
            ll wm_ll = (items[i].m * take + S_M - 1) / S_M;
            ll wl_ll = (items[i].l * take + S_L - 1) / S_L;
            if (wm_ll <= Tm && wl_ll <= Tl) {
                Chunk ch;
                ch.orig = i;
                ch.take = take;
                ch.wm = (int)wm_ll;
                ch.wl = (int)wl_ll;
                ch.value = items[i].v * take;
                chunks.push_back(ch);
            }
            qeff -= take;
            k <<= 1;
        }
    }
    int W = Tl + 1;
    vector<ll> dp((Tm + 1) * (Tl + 1), 0);
    vector<int> from((Tm + 1) * (Tl + 1), -1);
    for (int id = 0; id < (int)chunks.size(); ++id) {
        int wm = chunks[id].wm;
        int wl = chunks[id].wl;
        ll val = chunks[id].value;
        for (int tm = Tm; tm >= wm; --tm) {
            int base = tm * W;
            int prevBase = (tm - wm) * W;
            for (int tl = Tl; tl >= wl; --tl) {
                ll cand = dp[prevBase + (tl - wl)] + val;
                int idx = base + tl;
                if (cand > dp[idx]) {
                    dp[idx] = cand;
                    from[idx] = id;
                }
            }
        }
    }
    // reconstruct
    vector<ll> cnt(n, 0);
    int tm = Tm, tl = Tl;
    int idx = tm * W + tl;
    while (idx >= 0 && from[idx] != -1) {
        int id = from[idx];
        cnt[chunks[id].orig] += chunks[id].take;
        tm -= chunks[id].wm;
        tl -= chunks[id].wl;
        if (tm < 0 || tl < 0) break;
        idx = tm * W + tl;
    }
    // ensure not exceeding qcap due to any unforeseen (should not)
    for (int i = 0; i < n; ++i) if (cnt[i] > qcap[i]) cnt[i] = qcap[i];
    return cnt;
}

// Try to add 1 unit of item i by removing other items if needed
static inline bool try_add_by_removal(int i, vector<ll>& cnt, ll& remM, ll& remL, ll& totalVal, const vector<Category>& items, const vector<ll>& qcap) {
    if (cnt[i] >= qcap[i]) return false;
    ll mi = items[i].m, li = items[i].l, vi = items[i].v;
    ll needM = mi > remM ? (mi - remM) : 0;
    ll needL = li > remL ? (li - remL) : 0;
    if (needM == 0 && needL == 0) {
        cnt[i] += 1;
        remM -= mi;
        remL -= li;
        totalVal += vi;
        return true;
    }
    // candidate items to remove
    int n = (int)items.size();
    vector<int> cand;
    cand.reserve(n);
    for (int j = 0; j < n; ++j) {
        if (cnt[j] > 0) cand.push_back(j);
    }
    if (cand.empty()) return false;
    double dM = (double)needM / (double)M_CAP;
    double dL = (double)needL / (double)L_CAP;
    vector<pair<double,int>> order;
    order.reserve(cand.size());
    for (int j : cand) {
        double denom = dM * (double)items[j].m + dL * (double)items[j].l;
        if (denom <= 0) denom = 1e-18;
        double score = (double)items[j].v / denom;
        order.emplace_back(score, j);
    }
    sort(order.begin(), order.end(), [&](const pair<double,int>& a, const pair<double,int>& b){
        if (a.first != b.first) return a.first < b.first;
        return items[a.second].v < items[b.second].v;
    });
    ll freedM = 0, freedL = 0, lostVal = 0;
    vector<ll> removed(n, 0);
    for (auto &pr : order) {
        if (freedM >= needM && freedL >= needL) break;
        int j = pr.second;
        if (cnt[j] <= 0) continue;
        ll avail = cnt[j] - removed[j];
        if (avail <= 0) continue;
        ll needM_rem = needM > freedM ? (needM - freedM) : 0;
        ll needL_rem = needL > freedL ? (needL - freedL) : 0;
        ll rM = needM_rem == 0 ? 0 : ( (needM_rem + items[j].m - 1) / items[j].m );
        ll rL = needL_rem == 0 ? 0 : ( (needL_rem + items[j].l - 1) / items[j].l );
        ll r = max(rM, rL);
        if (r <= 0) continue;
        if (r > avail) r = avail;
        freedM += r * items[j].m;
        freedL += r * items[j].l;
        lostVal += r * items[j].v;
        removed[j] += r;
    }
    if (freedM >= needM && freedL >= needL && lostVal < vi) {
        for (int j = 0; j < n; ++j) {
            if (removed[j] > 0) {
                cnt[j] -= removed[j];
                remM += removed[j] * items[j].m;
                remL += removed[j] * items[j].l;
                totalVal -= removed[j] * items[j].v;
            }
        }
        cnt[i] += 1;
        remM -= mi;
        remL -= li;
        totalVal += vi;
        return true;
    }
    return false;
}

static inline void local_improve(vector<ll>& cnt, const vector<Category>& items, const vector<ll>& qcap) {
    ll val=0, usedM=0, usedL=0;
    computeTotals(items, cnt, val, usedM, usedL);
    ll remM = M_CAP - usedM;
    ll remL = L_CAP - usedL;
    if (remM < 0 || remL < 0) return; // Shouldn't happen
    // First try to fill leftover directly
    fill_leftover(cnt, items, qcap);
    computeTotals(items, cnt, val, usedM, usedL);
    remM = M_CAP - usedM;
    remL = L_CAP - usedL;

    int n = (int)items.size();
    // Order items by value density for attempts
    vector<int> order(n);
    for (int i = 0; i < n; ++i) order[i] = i;
    auto density = [&](int i)->double{
        double dm = (double)items[i].m / (double)M_CAP;
        double dl = (double)items[i].l / (double)L_CAP;
        double denom = dm + dl;
        if (denom <= 0) denom = 1e-18;
        return (double)items[i].v / denom;
    };
    sort(order.begin(), order.end(), [&](int a, int b){
        double da = density(a), db = density(b);
        if (da != db) return da > db;
        return items[a].v > items[b].v;
    });
    int maxPasses = 3;
    int operations_limit = 200; // accepted successful additions
    for (int pass = 0; pass < maxPasses && operations_limit > 0; ++pass) {
        bool improved = false;
        for (int idx = 0; idx < n && operations_limit > 0; ++idx) {
            int i = order[idx];
            // Try multiple times for this item
            int inner = 0;
            while (cnt[i] < qcap[i] && operations_limit > 0 && inner < 5) {
                bool ok = try_add_by_removal(i, cnt, remM, remL, val, items, qcap);
                if (!ok) break;
                improved = true;
                operations_limit--;
                inner++;
            }
        }
        if (!improved) break;
    }
    // Final fill with any leftover capacity
    fill_leftover(cnt, items, qcap);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    Parser parser(input);
    vector<Category> items;
    vector<string> names;
    // parse object
    // Expect '{'
    // We will scan for up to 12 entries
    // robustly: find each key and its 4 numbers
    while (true) {
        // find next key
        string key = parser.nextString();
        if (key.empty()) break;
        // find array with 4 numbers
        ll q = parser.nextInt();
        ll v = parser.nextInt();
        ll m = parser.nextInt();
        ll l = parser.nextInt();
        Category c;
        c.name = key;
        c.q = q;
        c.v = v;
        c.m = m;
        c.l = l;
        items.push_back(c);
        names.push_back(key);
        // move to next entry
        // this simple parser reads through numbers only; continue
    }
    int n = (int)items.size();
    if (n == 0) {
        // Output empty JSON
        cout << "{";
        bool first = true;
        for (auto &nm : names) {
            if (!first) cout << ", ";
            first = false;
            cout << " \"" << nm << "\": 0";
        }
        cout << " }";
        return 0;
    }
    // Cap q by physical single-item fit
    vector<ll> qcap(n);
    for (int i = 0; i < n; ++i) {
        ll maxByM = (items[i].m > 0) ? (M_CAP / items[i].m) : 0;
        ll maxByL = (items[i].l > 0) ? (L_CAP / items[i].l) : 0;
        ll cap = min(items[i].q, min(maxByM, maxByL));
        if (items[i].m > M_CAP || items[i].l > L_CAP) cap = 0;
        qcap[i] = max(0LL, cap);
    }

    // Generate candidates
    Solution best;
    best.cnt.assign(n, 0);
    best.value = 0;
    best.msum = 0;
    best.lsum = 0;

    auto consider = [&](const vector<ll>& cnt) {
        Solution s = makeSolution(items, cnt);
        if (s.msum <= M_CAP && s.lsum <= L_CAP && s.value > best.value) {
            best = s;
        }
    };

    // DP candidate
    {
        vector<ll> cnt = dp_solution(items, qcap);
        // Fill leftover greedily
        fill_leftover(cnt, items, qcap);
        consider(cnt);
    }

    // Greedy for multiple t
    vector<double> tvals;
    for (int k = 0; k <= 10; ++k) tvals.push_back(k / 10.0);
    // extra weights
    tvals.push_back(0.33);
    tvals.push_back(0.67);
    for (double t : tvals) {
        vector<ll> cnt = greedy_pack(items, t, qcap);
        consider(cnt);
    }

    // Try local improvement on best
    vector<ll> improved = best.cnt;
    local_improve(improved, items, qcap);
    consider(improved);

    // Output JSON with same keys as input
    cout << "{\n";
    for (int i = 0; i < n; ++i) {
        cout << " \"" << items[i].name << "\": " << best.cnt[i];
        if (i + 1 < n) cout << ",\n";
        else cout << "\n";
    }
    cout << "}";
    return 0;
}