#include <bits/stdc++.h>
using namespace std;

int n;

int ask(int i, int j){
    cout << "? " << i << " " << j << endl;
    cout.flush();
    int x;
    if(!(cin >> x)) exit(0);
    if(x == -1) exit(0);
    return x;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if(!(cin >> n)) return 0;

    vector<int> ids(n);
    iota(ids.begin(), ids.end(), 1);
    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
    shuffle(ids.begin(), ids.end(), rng);

    int a = ids[0], b = ids[1];

    struct Rec { int k, a, b, qa, qb; };
    vector<Rec> recs;

    for(int t = 2; t < n; ++t){
        int k = ids[t];
        int qa = ask(a, k);
        int qb = ask(b, k);
        recs.push_back({k, a, b, qa, qb});
        if(qa < qb) b = k;
        else if(qb < qa) a = k;
        // if equal, keep as is
    }

    int z = -1;
    for(int c : ids){
        if(c == a || c == b) continue;
        int qa = ask(a, c);
        int qb = ask(b, c);
        if(qa < qb){ z = a; break; }
        if(qb < qa){ z = b; break; }
    }
    if(z == -1){
        // As a fallback (theoretically shouldn't happen), try all
        for(int c = 1; c <= n; ++c){
            if(c == a || c == b) continue;
            int qa = ask(a, c);
            int qb = ask(b, c);
            if(qa < qb){ z = a; break; }
            if(qb < qa){ z = b; break; }
        }
    }
    if(z == -1){
        // last resort: compare a and b via some d
        int d = 1;
        if(d == a || d == b) d = 2;
        int qa = ask(a, d);
        int qb = ask(b, d);
        if(qa < qb) z = a; else z = b;
    }

    vector<int> res(n+1, -1);
    res[z] = 0;

    for(auto &r : recs){
        if(r.a == z) res[r.k] = r.qa;
        else if(r.b == z) res[r.k] = r.qb;
    }

    for(int i = 1; i <= n; ++i){
        if(i == z) continue;
        if(res[i] == -1){
            res[i] = ask(z, i);
        }
    }

    cout << "! ";
    for(int i = 1; i <= n; ++i){
        cout << res[i] << (i == n ? '\n' : ' ');
    }
    cout.flush();

    return 0;
}