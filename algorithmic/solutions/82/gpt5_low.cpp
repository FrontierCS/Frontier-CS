#include <bits/stdc++.h>
using namespace std;

static mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

int n;

int ask(int i, int j){
    cout << "? " << i << " " << j << endl;
    cout.flush();
    int x;
    if(!(cin >> x)) exit(0);
    if(x == -1) exit(0);
    return x;
}

void answer(const vector<int>& p){
    cout << "! ";
    for(int i=1;i<=n;i++){
        cout << p[i] << (i==n?'\n':' ');
    }
    cout.flush();
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if(!(cin >> n)) return 0;

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 1);

    auto full_sweep = [&](int r, vector<int>& sweeps, int &pr){
        sweeps.assign(n+1, -1);
        int all_and = (1<<12)-1; // since n<=2048 -> values use up to 11 bits
        for(int i=1;i<=n;i++){
            if(i==r) continue;
            int v = ask(r,i);
            sweeps[i] = v;
            all_and &= v;
        }
        pr = all_and;
    };

    auto get_candidates = [&](const vector<int>& sweeps, int target){
        vector<int> cand;
        for(int i=1;i<=n;i++){
            if(sweeps[i] == target) cand.push_back(i);
        }
        return cand;
    };

    auto eliminate_zero = [&](vector<int> C, const vector<int>& avoid){
        vector<char> avoidMark(n+1, false);
        for(int a: avoid) if(a>=1 && a<=n) avoidMark[a]=true;
        uniform_int_distribution<int> dist(1, n);
        int rounds = 0;
        while(C.size() > 1 && rounds < 64){
            int j = dist(rng);
            int tries = 0;
            while((avoidMark[j]) && tries < 4*n){
                j = dist(rng);
                tries++;
            }
            // If we failed to find a non-avoid index, just proceed with current j
            vector<pair<int,int>> vals; vals.reserve(C.size());
            int mn = INT_MAX;
            for(int t: C){
                int v = ask(t, j);
                vals.emplace_back(t, v);
                if(v < mn) mn = v;
            }
            vector<int> C2;
            for(auto &pr: vals){
                if(pr.second == mn) C2.push_back(pr.first);
            }
            if(C2.size() < C.size()){
                C.swap(C2);
            }
            rounds++;
        }
        return C.empty() ? -1 : C[0];
    };

    while(true){
        int r1 = uniform_int_distribution<int>(1,n)(rng);
        vector<int> s1;
        int pr1;
        full_sweep(r1, s1, pr1);
        if(pr1 == 0){
            vector<int> p(n+1, 0);
            for(int i=1;i<=n;i++){
                if(i==r1) p[i]=0;
                else p[i]=s1[i];
            }
            answer(p);
            return 0;
        }

        vector<int> T = get_candidates(s1, pr1);
        int r2;
        if(!T.empty()){
            r2 = T[uniform_int_distribution<int>(0,(int)T.size()-1)(rng)];
        }else{
            r2 = uniform_int_distribution<int>(1,n)(rng);
            if(r2==r1) r2 = (r2 % n) + 1;
        }

        vector<int> s2;
        int pr2;
        full_sweep(r2, s2, pr2);
        if(pr2 == 0){
            vector<int> p(n+1, 0);
            for(int i=1;i<=n;i++){
                if(i==r2) p[i]=0;
                else p[i]=s2[i];
            }
            answer(p);
            return 0;
        }

        vector<int> T2 = get_candidates(s2, pr2);
        // Try to identify zero among T2
        int z = -1;
        {
            vector<int> avoid = {r1, r2};
            z = eliminate_zero(T2.empty() ? T : T2, avoid);
            if(z == -1){
                // fallback: pick any from T2 or T
                z = !T2.empty() ? T2[0] : (!T.empty() ? T[0] : 1);
            }
        }

        // Verify and recover permutation from z
        vector<int> p(n+1, 0);
        for(int i=1;i<=n;i++){
            if(i==z){ p[i]=0; continue; }
            p[i] = ask(z, i);
        }
        answer(p);
        return 0;
    }

    return 0;
}