#include <bits/stdc++.h>
using namespace std;

struct Candidate {
    long long sum;
    unsigned long long lo;
    unsigned long long hi;
};

static inline long long absll(long long x){ return x >= 0 ? x : -x; }

static inline bool getbit(const Candidate &c, int i){
    if(i < 64) return (c.lo >> i) & 1ULL;
    return (c.hi >> (i - 64)) & 1ULL;
}

static inline void setbit(Candidate &c, int i){
    if(i < 64) c.lo |= (1ULL << i);
    else c.hi |= (1ULL << (i - 64));
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    long long T;
    if(!(cin >> n >> T)) return 0;
    vector<long long> a(n);
    for(int i=0;i<n;i++) cin >> a[i];

    // Beam width
    int K;
    if(n <= 40) K = 80000;
    else if(n <= 70) K = 50000;
    else K = 35000;

    vector<Candidate> cur, nxt;
    cur.reserve((size_t)K);
    nxt.reserve((size_t)K * 2);

    Candidate best;
    best.sum = 0;
    best.lo = 0;
    best.hi = 0;
    long long bestDiff = absll(0 - T);

    // Initialize
    Candidate base;
    base.sum = 0;
    base.lo = 0;
    base.hi = 0;
    cur.push_back(base);

    for(int i=0;i<n;i++){
        nxt.clear();
        nxt.reserve(cur.size() * 2);
        // Without including a[i]
        for(size_t j=0;j<cur.size();j++){
            nxt.push_back(cur[j]);
        }
        // Including a[i]
        for(size_t j=0;j<cur.size();j++){
            Candidate c = cur[j];
            c.sum += a[i];
            setbit(c, i);
            nxt.push_back(c);
        }
        // Update best while scanning
        for(size_t j=0;j<nxt.size();j++){
            long long d = absll(nxt[j].sum - T);
            if(d < bestDiff){
                bestDiff = d;
                best = nxt[j];
                if(bestDiff == 0){
                    // Perfect match
                    string out(n, '0');
                    for(int k=0;k<n;k++){
                        out[k] = getbit(best, k) ? '1' : '0';
                    }
                    cout << out << "\n";
                    return 0;
                }
            }
        }
        // Keep only top K by closeness to T
        if((int)nxt.size() > K){
            nth_element(nxt.begin(), nxt.begin() + K, nxt.end(), [&](const Candidate &x, const Candidate &y){
                long long dx = absll(x.sum - T);
                long long dy = absll(y.sum - T);
                if(dx != dy) return dx < dy;
                return x.sum < y.sum;
            });
            nxt.resize(K);
        }
        cur.swap(nxt);
    }

    // Local improvement: 1-flip hill climbing, then random 2-flip attempts
    unsigned long long lo = best.lo, hi = best.hi;
    long long curSum = best.sum;
    long long curDiff = absll(curSum - T);

    auto getbit2 = [&](int i)->bool{
        if(i < 64) return (lo >> i) & 1ULL;
        return (hi >> (i - 64)) & 1ULL;
    };
    auto flipbit2 = [&](int i){
        if(i < 64) lo ^= (1ULL << i);
        else hi ^= (1ULL << (i - 64));
    };

    // 1-flip improvement
    while(true){
        int besti = -1;
        long long bestNewSum = curSum;
        long long bestNewDiff = curDiff;
        for(int i=0;i<n;i++){
            bool in = getbit2(i);
            long long ns = in ? (curSum - a[i]) : (curSum + a[i]);
            long long nd = absll(ns - T);
            if(nd < bestNewDiff){
                bestNewDiff = nd;
                bestNewSum = ns;
                besti = i;
            }
        }
        if(besti == -1) break;
        // apply
        flipbit2(besti);
        curSum = bestNewSum;
        curDiff = bestNewDiff;
        if(curDiff == 0) break;
    }

    // Random 2-flip improvements
    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(0, n-1);
    int attempts = 0;
    int maxAttempts = 20000;
    while(attempts < maxAttempts && curDiff > 0){
        int i = dist(rng);
        int j = dist(rng);
        if(j == i){
            j = (j + 1) % n;
        }
        bool in_i = getbit2(i);
        bool in_j = getbit2(j);
        long long ns = curSum + (in_i ? -a[i] : a[i]) + (in_j ? -a[j] : a[j]);
        long long nd = absll(ns - T);
        if(nd < curDiff){
            // apply both flips
            flipbit2(i);
            flipbit2(j);
            curSum = ns;
            curDiff = nd;
            // try 1-flip improvements again
            while(true){
                int besti = -1;
                long long bestNewSum = curSum;
                long long bestNewDiff = curDiff;
                for(int k=0;k<n;k++){
                    bool in = getbit2(k);
                    long long nss = in ? (curSum - a[k]) : (curSum + a[k]);
                    long long ndd = absll(nss - T);
                    if(ndd < bestNewDiff){
                        bestNewDiff = ndd;
                        bestNewSum = nss;
                        besti = k;
                    }
                }
                if(besti == -1) break;
                flipbit2(besti);
                curSum = bestNewSum;
                curDiff = bestNewDiff;
                if(curDiff == 0) break;
            }
        }
        attempts++;
    }

    string out(n, '0');
    for(int k=0;k<n;k++){
        bool b = (k < 64) ? ((lo >> k) & 1ULL) : ((hi >> (k - 64)) & 1ULL);
        out[k] = b ? '1' : '0';
    }
    cout << out << "\n";
    return 0;
}