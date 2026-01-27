#include <bits/stdc++.h>
using namespace std;

static const int H = 8, W = 14, N = H * W;

struct Mask {
    uint64_t lo, hi;
    Mask(uint64_t a=0, uint64_t b=0): lo(a), hi(b) {}
    inline void reset() { lo = hi = 0; }
    inline bool any() const { return (lo | hi) != 0; }
    inline void OR(const Mask& o){ lo |= o.lo; hi |= o.hi; }
    inline void AND(const Mask& o){ lo &= o.lo; hi &= o.hi; }
};

static Mask neigh[N];

inline int idx(int r, int c){ return r*W + c; }

void build_neighbors() {
    for (int r=0; r<H; ++r){
        for (int c=0; c<W; ++c){
            int i = idx(r,c);
            uint64_t lo=0, hi=0;
            for (int dr=-1; dr<=1; ++dr){
                for (int dc=-1; dc<=1; ++dc){
                    if (dr==0 && dc==0) continue;
                    int nr=r+dr, nc=c+dc;
                    if (0<=nr && nr<H && 0<=nc && nc<W){
                        int j = idx(nr,nc);
                        if (j < 64) lo |= (1ull<<j);
                        else hi |= (1ull<<(j-64));
                    }
                }
            }
            neigh[i] = Mask(lo,hi);
        }
    }
}

struct Grid {
    array<int, N> a;
};

Mask digit_mask[10];

inline void build_digit_masks(const Grid& g){
    for (int d=0; d<10; ++d) digit_mask[d].reset();
    for (int i=0; i<N; ++i){
        int d = g.a[i];
        if (i < 64) digit_mask[d].lo |= (1ull<<i);
        else digit_mask[d].hi |= (1ull<<(i-64));
    }
}

inline bool readable_digits(const vector<int>& ds){
    if (ds.empty()) return false;
    Mask cur = digit_mask[ds[0]];
    if (!cur.any()) return false;
    for (size_t k=1; k<ds.size(); ++k){
        Mask nxt(0,0);
        uint64_t x = cur.lo;
        while (x){
            int b = __builtin_ctzll(x);
            nxt.OR(neigh[b]);
            x &= x-1;
        }
        x = cur.hi;
        while (x){
            int b = __builtin_ctzll(x);
            nxt.OR(neigh[64 + b]);
            x &= x-1;
        }
        nxt.AND(digit_mask[ds[k]]);
        if (!nxt.any()) return false;
        cur = nxt;
    }
    return true;
}

static vector<vector<int>> numDigits;

void precompute_numbers(int maxN){
    numDigits.assign(maxN+1, {});
    for (int n=0; n<=maxN; ++n){
        if (n==0){
            numDigits[n] = {0};
            continue;
        }
        int x = n;
        vector<int> ds;
        while (x>0){
            ds.push_back(x%10);
            x/=10;
        }
        reverse(ds.begin(), ds.end());
        numDigits[n] = move(ds);
    }
}

int calcScore(const Grid& g, int limit){
    build_digit_masks(g);
    for (int n=1; n<=limit; ++n){
        if (!readable_digits(numDigits[n])){
            return n-1;
        }
    }
    return limit;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    build_neighbors();

    const int PRE_MAX = 5000;
    precompute_numbers(PRE_MAX);

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dig(0,9);

    auto start = chrono::steady_clock::now();
    auto deadline = start + chrono::milliseconds(58000);

    Grid best;
    for (int i=0;i<N;++i) best.a[i]=dig(rng);
    int bestScore;
    {
        int limit = 150;
        bestScore = calcScore(best, min(limit, PRE_MAX));
    }

    Grid cand;
    int iter = 0;

    // Phase 1: random restarts
    while (chrono::steady_clock::now() < deadline) {
        ++iter;
        for (int i=0;i<N;++i) cand.a[i]=dig(rng);
        int baseLimit = max(bestScore + 30, 130);
        baseLimit = min(baseLimit, PRE_MAX);
        int s = calcScore(cand, baseLimit);
        if (s > bestScore){
            // verify further to solidify advantage
            int verifyLimit = min(max(s + 100, bestScore + 100), PRE_MAX);
            int s2 = calcScore(cand, verifyLimit);
            if (s2 > bestScore){
                best = cand;
                bestScore = s2;
            }
        }
        // Occasionally do a local improvement around the current best
        if ((iter & 127) == 0 && chrono::steady_clock::now() < deadline){
            Grid local = best;
            int localLimit = min(bestScore + 50, PRE_MAX);
            for (int t=0; t<500 && chrono::steady_clock::now() < deadline; ++t){
                int changes = 1 + (rng() % 2);
                vector<pair<int,int>> mods;
                mods.reserve(changes);
                for (int k=0;k<changes;++k){
                    int pos = rng() % N;
                    int old = local.a[pos];
                    int nd = dig(rng);
                    if (nd == old) nd = (nd + 1 + (rng()%9)) % 10;
                    mods.push_back({pos, old});
                    local.a[pos] = nd;
                }
                int sLoc = calcScore(local, localLimit);
                if (sLoc > bestScore){
                    int sFull = calcScore(local, min(sLoc + 200, PRE_MAX));
                    if (sFull > bestScore){
                        best = local;
                        bestScore = sFull;
                        localLimit = min(bestScore + 50, PRE_MAX);
                    }
                } else {
                    // revert
                    for (auto &pr: mods) local.a[pr.first] = pr.second;
                }
            }
        }
    }

    // Output best grid
    for (int r=0;r<H;++r){
        for (int c=0;c<W;++c){
            cout << best.a[idx(r,c)];
        }
        cout << '\n';
    }
    return 0;
}