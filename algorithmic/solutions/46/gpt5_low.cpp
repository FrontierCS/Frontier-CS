#include <bits/stdc++.h>
using namespace std;

struct RNG {
    uint64_t x;
    RNG(uint64_t seed=88172645463393265ull){ x=seed; }
    uint64_t next() { x ^= x<<7; x ^= x>>9; return x; }
    int nextInt(int n){ return (int)(next()%n); }
    double nextDouble(){ return (next()>>11) * (1.0/9007199254740992.0); }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int J,M;
    if(!(cin>>J>>M)) return 0;
    vector<vector<int>> route(J, vector<int>(M));
    vector<vector<long long>> proc(J, vector<long long>(M));
    for(int j=0;j<J;j++){
        for(int k=0;k<M;k++){
            int m; long long p;
            cin>>m>>p;
            route[j][k]=m;
            proc[j][k]=p;
        }
    }
    // Precompute remaining processing time from each index
    vector<vector<long long>> remFrom(J, vector<long long>(M+1,0));
    for(int j=0;j<J;j++){
        for(int k=M-1;k>=0;k--){
            remFrom[j][k]=remFrom[j][k+1]+proc[j][k];
        }
    }
    // Machine workloads
    vector<long long> machineLoad(M,0);
    for(int j=0;j<J;j++){
        for(int k=0;k<M;k++){
            machineLoad[ route[j][k] ] += proc[j][k];
        }
    }

    struct Best {
        long long makespan = (1LL<<62);
        vector<vector<int>> order;
    } best;

    RNG rng( chrono::high_resolution_clock::now().time_since_epoch().count() ^ (uint64_t)(J*1315423911u + M*2654435761u) );

    auto buildSchedule = [&](int ruleId)->pair<long long, vector<vector<int>>>{
        vector<int> nextOp(J,0);
        vector<long long> jobReady(J,0);
        vector<long long> machReady(M,0);
        vector<vector<int>> order(M);
        order.assign(M, {});
        long long makespan=0;
        int remaining = J*M;

        while(remaining>0){
            // gather ready operations (next operation of every unfinished job)
            struct Cand {
                int j, k, m;
                long long p, r, s, rem;
                long long key1, key2, key3;
                double rnd;
            };
            vector<Cand> C;
            C.reserve(J);
            long long bestS = (1LL<<62);
            for(int j=0;j<J;j++){
                int k = nextOp[j];
                if(k>=M) continue;
                int m = route[j][k];
                long long p = proc[j][k];
                long long r = jobReady[j];
                long long s = max(r, machReady[m]);
                long long rem = remFrom[j][k];
                Cand cand;
                cand.j=j; cand.k=k; cand.m=m; cand.p=p; cand.r=r; cand.s=s; cand.rem=rem;
                cand.rnd = rng.nextDouble();
                // compute keys per rule
                switch(ruleId){
                    case 0: // earliest start, SPT
                        cand.key1 = s;
                        cand.key2 = p;
                        cand.key3 = j;
                        break;
                    case 1: // earliest start, LPT
                        cand.key1 = s;
                        cand.key2 = -p;
                        cand.key3 = j;
                        break;
                    case 2: // earliest release, SPT
                        cand.key1 = r;
                        cand.key2 = p;
                        cand.key3 = s;
                        break;
                    case 3: // earliest start, largest remaining work
                        cand.key1 = s;
                        cand.key2 = -rem;
                        cand.key3 = -p;
                        break;
                    case 4: { // bottleneck aware: prefer ops on heaviest machines, earliest start
                        long long load = machineLoad[m];
                        cand.key1 = s;
                        cand.key2 = -load;
                        cand.key3 = p;
                        break;
                    }
                    case 5: { // combination: (s, -rem, -machineLoad, -p)
                        cand.key1 = s;
                        cand.key2 = -rem - (machineLoad[m]>>20);
                        cand.key3 = - (long long)p;
                        break;
                    }
                    default:
                        cand.key1 = s; cand.key2 = p; cand.key3 = j;
                }
                C.push_back(cand);
                if(s < bestS) bestS = s;
            }
            // Among candidates, pick the best according to keys; small randomness to diversify ties
            auto cmp = [&](const Cand& a, const Cand& b){
                if(a.key1 != b.key1) return a.key1 < b.key1;
                if(a.key2 != b.key2) return a.key2 < b.key2;
                if(a.key3 != b.key3) return a.key3 < b.key3;
                return a.rnd < b.rnd;
            };
            // Optional: restrict to those with minimal s to be more non-delay
            // Gather subset with s close to bestS (non-delay)
            vector<Cand> subset;
            subset.reserve(C.size());
            for(auto &c: C){
                if(c.s == bestS) subset.push_back(c);
            }
            if(subset.empty()) subset = C;
            // Choose best from subset per keys
            Cand chosen = *min_element(subset.begin(), subset.end(), cmp);

            // Schedule chosen
            int j = chosen.j;
            int k = chosen.k;
            int m = chosen.m;
            long long p = chosen.p;
            long long s = max(jobReady[j], machReady[m]);
            long long f = s + p;

            order[m].push_back(j);
            jobReady[j] = f;
            machReady[m] = f;
            nextOp[j]++;
            makespan = max(makespan, f);
            remaining--;
        }
        return {makespan, order};
    };

    int iterations = 200;
    // Scale iterations with problem size modestly
    int N = J*M;
    iterations = min(600, max(60, (int)(200 + N/3)));
    vector<int> rules = {0,1,2,3,4,5};
    // Ensure we at least try each rule once deterministically
    for(int rid : rules){
        auto res = buildSchedule(rid);
        if(res.first < best.makespan){
            best.makespan = res.first;
            best.order = move(res.second);
        }
    }
    for(int it=0; it<iterations; ++it){
        int rid = rules[rng.nextInt((int)rules.size())];
        auto res = buildSchedule(rid);
        if(res.first < best.makespan){
            best.makespan = res.first;
            best.order = move(res.second);
        }
    }

    // Output machine orders (each line J integers)
    for(int m=0;m<M;m++){
        // As a safeguard, if for some reason we didn't collect exactly J jobs, fill missing with any not present.
        if((int)best.order[m].size() != J){
            vector<int> seen(J,0);
            for(int x: best.order[m]) if(0<=x && x<J) seen[x]=1;
            for(int j=0;j<J;j++) if(!seen[j]) best.order[m].push_back(j);
            if((int)best.order[m].size()>J) best.order[m].resize(J);
        }
        for(int idx=0; idx<J; ++idx){
            if(idx) cout << ' ';
            cout << best.order[m][idx];
        }
        cout << '\n';
    }
    return 0;
}