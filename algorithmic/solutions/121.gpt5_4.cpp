#include <bits/stdc++.h>
using namespace std;

static inline int code(char c) {
    if (c=='A') return 0;
    if (c=='C') return 1;
    if (c=='G') return 2;
    if (c=='T') return 3;
    return -1;
}

// 64-bit path
long double solve64(int n, int m, const vector<string>& s) {
    uint64_t full = (m == 64 ? ~0ULL : ((1ULL << m) - 1ULL));

    // allowed masks per position and letter
    vector<array<uint64_t,4>> allow(n);
    for (int j = 0; j < n; ++j) {
        allow[j][0] = allow[j][1] = allow[j][2] = allow[j][3] = 0;
    }
    for (int i = 0; i < m; ++i) {
        uint64_t bit = (1ULL << i);
        for (int j = 0; j < n; ++j) {
            int c = code(s[i][j]);
            if (c == -1) {
                allow[j][0] |= bit;
                allow[j][1] |= bit;
                allow[j][2] |= bit;
                allow[j][3] |= bit;
            } else {
                allow[j][c] |= bit;
            }
        }
    }

    // compress letter classes per position
    struct MaskGroup { uint64_t mask; int cnt; };
    vector<vector<MaskGroup>> groups(n);
    for (int j = 0; j < n; ++j) {
        // group identical masks among 4 letters
        vector<MaskGroup> g;
        for (int x = 0; x < 4; ++x) {
            uint64_t msk = allow[j][x];
            bool found = false;
            for (auto &pg : g) {
                if (pg.mask == msk) {
                    pg.cnt++;
                    found = true;
                    break;
                }
            }
            if (!found) g.push_back({msk, 1});
        }
        groups[j] = move(g);
    }

    unordered_map<uint64_t, long double> cur;
    cur.reserve(1024);
    cur[full] = 1.0L;

    for (int j = 0; j < n; ++j) {
        unordered_map<uint64_t, long double> nxt;
        nxt.reserve(cur.size() * groups[j].size() + 4);
        for (auto &kv : cur) {
            uint64_t state = kv.first;
            long double p = kv.second;
            for (auto &g : groups[j]) {
                uint64_t ns = state & g.mask;
                nxt[ns] += p * ( (long double)g.cnt * 0.25L );
            }
        }
        cur.swap(nxt);
    }

    long double p_invalid = 0.0L;
    auto it = cur.find(0ULL);
    if (it != cur.end()) p_invalid = it->second;
    long double ans = 1.0L - p_invalid;
    return ans;
}

// General bitset path for m > 64
struct VecHash {
    size_t operator()(const string& s) const noexcept {
        // splitmix64 over chunks
        const uint64_t* data = reinterpret_cast<const uint64_t*>(s.data());
        size_t n = s.size() / 8;
        auto splitmix64 = [](uint64_t x) {
            x += 0x9e3779b97f4a7c15ULL;
            x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
            x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
            x = x ^ (x >> 31);
            return x;
        };
        uint64_t h = 0;
        for (size_t i = 0; i < n; ++i) {
            h ^= splitmix64(data[i] + 0x9e3779b97f4a7c15ULL + (h<<6) + (h>>2));
        }
        return (size_t)h;
    }
};

long double solveBig(int n, int m, const vector<string>& s) {
    int W = (m + 63) / 64;
    vector<uint64_t> full(W, ~0ULL);
    if (m % 64 != 0) {
        full[W-1] = (m % 64 == 0) ? ~0ULL : ((1ULL << (m % 64)) - 1ULL);
    }

    // allowed masks per position and letter
    vector<array<vector<uint64_t>,4>> allow(n);
    for (int j = 0; j < n; ++j) {
        for (int x = 0; x < 4; ++x) allow[j][x].assign(W, 0ULL);
    }
    for (int i = 0; i < m; ++i) {
        int wi = i / 64, bi = i % 64;
        uint64_t bit = (1ULL << bi);
        for (int j = 0; j < n; ++j) {
            int c = code(s[i][j]);
            if (c == -1) {
                for (int x = 0; x < 4; ++x) allow[j][x][wi] |= bit;
            } else {
                allow[j][c][wi] |= bit;
            }
        }
    }

    auto equalsVec = [&](const vector<uint64_t>& a, const vector<uint64_t>& b)->bool {
        for (int k = 0; k < W; ++k) if (a[k] != b[k]) return false;
        return true;
    };

    // compress letter classes per position
    vector<vector<vector<uint64_t>>> masks(n);
    vector<vector<int>> weights(n);
    vector<vector<char>> isFull(n);
    for (int j = 0; j < n; ++j) {
        vector<vector<uint64_t>> uniq;
        vector<int> w;
        vector<char> f;
        for (int x = 0; x < 4; ++x) {
            const vector<uint64_t>& v = allow[j][x];
            bool found = false;
            for (size_t t = 0; t < uniq.size(); ++t) {
                if (equalsVec(uniq[t], v)) {
                    w[t] += 1;
                    found = true;
                    break;
                }
            }
            if (!found) {
                uniq.push_back(v);
                w.push_back(1);
            }
        }
        f.assign(uniq.size(), 0);
        for (size_t t = 0; t < uniq.size(); ++t) {
            if (equalsVec(uniq[t], full)) f[t] = 1;
        }
        masks[j] = move(uniq);
        weights[j] = move(w);
        isFull[j] = move(f);
    }

    // state pool and mapping: vector<uint64_t> -> id
    vector<vector<uint64_t>> states;
    states.reserve(1024);
    unordered_map<string, int, VecHash> idmap;
    idmap.reserve(2048);

    auto keyFromVec = [&](const vector<uint64_t>& v)->string {
        string k;
        k.resize((size_t)W * 8);
        memcpy(&k[0], v.data(), (size_t)W * 8);
        return k;
    };

    // Add full and zero states
    vector<uint64_t> zero(W, 0ULL);
    string keyFull = keyFromVec(full);
    string keyZero = keyFromVec(zero);
    states.push_back(full);
    idmap.emplace(keyFull, 0);
    int zeroID;
    if (keyZero == keyFull) {
        zeroID = 0;
    } else {
        states.push_back(zero);
        idmap.emplace(keyZero, 1);
        zeroID = 1;
    }

    unordered_map<int, long double> cur;
    cur.reserve(1024);
    cur[0] = 1.0L; // full set id == 0

    vector<uint64_t> tmp(W);
    for (int j = 0; j < n; ++j) {
        unordered_map<int, long double> nxt;
        nxt.reserve(cur.size() * masks[j].size() + 4);
        for (auto &kv : cur) {
            int id = kv.first;
            long double p = kv.second;
            const vector<uint64_t>& st = states[id];
            for (size_t t = 0; t < masks[j].size(); ++t) {
                long double add = p * ((long double)weights[j][t] * 0.25L);
                if (isFull[j][t]) {
                    nxt[id] += add;
                } else {
                    const vector<uint64_t>& maskv = masks[j][t];
                    for (int k = 0; k < W; ++k) tmp[k] = st[k] & maskv[k];
                    string kstr;
                    kstr.resize((size_t)W * 8);
                    memcpy(&kstr[0], tmp.data(), (size_t)W * 8);
                    auto it = idmap.find(kstr);
                    int nid;
                    if (it == idmap.end()) {
                        nid = (int)states.size();
                        states.push_back(tmp);
                        idmap.emplace(move(kstr), nid);
                    } else {
                        nid = it->second;
                    }
                    nxt[nid] += add;
                }
            }
        }
        cur.swap(nxt);
    }

    long double p_invalid = 0.0L;
    auto it = cur.find(zeroID);
    if (it != cur.end()) p_invalid = it->second;
    long double ans = 1.0L - p_invalid;
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> sraw;
    sraw.reserve(m);
    for (int i = 0; i < m; ++i) {
        string t; cin >> t;
        sraw.push_back(t);
    }
    // Deduplicate
    unordered_set<string> seen;
    seen.reserve(m*2+1);
    vector<string> s;
    s.reserve(m);
    bool allQuestionExists = false;
    for (auto &t : sraw) {
        if (seen.insert(t).second) {
            s.push_back(t);
            bool allq = true;
            for (char c : t) if (c != '?') { allq = false; break; }
            if (allq) allQuestionExists = true;
        }
    }
    if (allQuestionExists) {
        cout.setf(std::ios::fixed); cout << setprecision(15) << 1.0L << "\n";
        return 0;
    }
    m = (int)s.size();
    long double ans;
    if (m <= 64) ans = solve64(n, m, s);
    else ans = solveBig(n, m, s);
    cout.setf(std::ios::fixed);
    cout << setprecision(15) << ans << "\n";
    return 0;
}