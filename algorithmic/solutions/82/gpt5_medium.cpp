#include <bits/stdc++.h>
using namespace std;

int n;

struct QueryCache {
    int n;
    unordered_map<long long, int> mp;
    QueryCache(int n_): n(n_) { mp.reserve(1<<20); }
    long long key(int i, int j){
        if(i>j) swap(i,j);
        return (long long)i*(n+1) + j;
    }
    bool has(int i, int j){
        return mp.find(key(i,j)) != mp.end();
    }
    int get(int i, int j){
        return mp[key(i,j)];
    }
    void set(int i, int j, int val){
        mp[key(i,j)] = val;
    }
};

int ask(int i, int j, QueryCache &cache){
    if(i==j){
        // Invalid, but should not happen
        return -1;
    }
    if(cache.has(i,j)) return cache.get(i,j);
    cout << "? " << i << " " << j << endl;
    cout.flush();
    int ans;
    if(!(cin >> ans)) exit(0);
    if(ans == -1) exit(0);
    cache.set(i,j,ans);
    return ans;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if(!(cin >> n)) return 0;

    QueryCache cache(n);
    mt19937 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // Initial random index r1
    int r1 = uniform_int_distribution<int>(1, n)(rng);

    vector<int> cand;
    cand.reserve(n);

    int minVal = INT_MAX;
    vector<int> val(n+1, -1);

    for(int i=1;i<=n;i++){
        if(i==r1) continue;
        int v = ask(i, r1, cache);
        val[i] = v;
        if(v < minVal) minVal = v;
    }
    for(int i=1;i<=n;i++){
        if(i==r1) continue;
        if(val[i] == minVal) cand.push_back(i);
    }

    // Narrow down candidates
    vector<int> nextCand;
    nextCand.reserve(n);
    vector<int> idxs;
    idxs.reserve(n);
    for(int i=1;i<=n;i++) idxs.push_back(i);

    // While multiple candidates remain
    while(cand.size() > 1){
        // choose r not in cand
        int r = -1;
        // attempt a few times to pick r outside cand
        for(int tries=0; tries<100; ++tries){
            int t = idxs[uniform_int_distribution<int>(0, n-1)(rng)];
            bool inCand = false;
            for(int x : cand){ if(x==t){ inCand=true; break; } }
            if(!inCand){ r = t; break; }
        }
        if(r == -1){
            // fallback: pick any index not in cand by scanning
            vector<char> mark(n+1, false);
            for(int x: cand) mark[x]=true;
            for(int i=1;i<=n;i++){
                if(!mark[i]) { r=i; break; }
            }
            if(r==-1){
                // All indices are candidates; pick r1 if not in cand
                // but this implies cand size == n which shouldn't happen after first step
                // choose r = r1 (guaranteed r1 not in initial cand if initial cand size == n-1 when p[r1]=all ones)
                r = r1;
            }
        }
        int curMin = INT_MAX;
        nextCand.clear();
        for(int i : cand){
            if(i==r) continue; // invalid query
            int v = ask(i, r, cache);
            if(v < curMin) curMin = v;
        }
        for(int i : cand){
            if(i==r) continue;
            int v = cache.get(i, r);
            if(v == curMin) nextCand.push_back(i);
        }
        cand.swap(nextCand);
    }

    int zeroIdx = cand[0];

    vector<int> p(n+1, -1);
    p[zeroIdx] = 0;
    for(int i=1;i<=n;i++){
        if(i==zeroIdx) continue;
        p[i] = ask(i, zeroIdx, cache);
    }

    cout << "! ";
    for(int i=1;i<=n;i++){
        if(i>1) cout << ' ';
        cout << p[i];
    }
    cout << endl;
    cout.flush();
    return 0;
}