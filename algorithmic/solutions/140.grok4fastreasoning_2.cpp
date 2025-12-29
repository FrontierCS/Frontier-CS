#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
const ll MAXC = 100000000LL;
const ll INF = 2 * MAXC;
int kk;
vector<ll> uu, vv;
ll p1, q1, p2, q2;
vector<ll> dist11, dist22;
bool recurse(int pos, vector<bool>& used, multiset<ll>& r1, multiset<ll>& r2, vector<int>& pairing) {
    if (pos == kk) return true;
    for (int j = 0; j < kk; ++j) {
        if (used[j]) continue;
        ll dd1 = max( abs(uu[pos] - p1) , abs(vv[j] - q1) );
        ll dd2 = max( abs(uu[pos] - p2) , abs(vv[j] - q2) );
        auto it1 = r1.find(dd1);
        auto it2 = r2.find(dd2);
        if (it1 != r1.end() && it2 != r2.end()) {
            r1.erase(it1);
            r2.erase(it2);
            used[j] = true;
            pairing[pos] = j;
            if (recurse(pos + 1, used, r1, r2, pairing)) return true;
            used[j] = false;
            r1.insert(dd1);
            r2.insert(dd2);
        }
    }
    return false;
}
int main() {
    ll b, w;
    cin >> b >> kk >> w;
    ll s = MAXC, t = MAXC;
    cout << "? 1 " << s << " " << t << endl;
    cout.flush();
    vector<ll> du(kk);
    for(int i=0; i<kk; i++) cin >> du[i];
    uu.resize(kk);
    for(int i=0; i<kk; i++) uu[i] = INF - du[i];
    s = MAXC; t = -MAXC;
    cout << "? 1 " << s << " " << t << endl;
    cout.flush();
    vector<ll> dv(kk);
    for(int i=0; i<kk; i++) cin >> dv[i];
    vv.resize(kk);
    for(int i=0; i<kk; i++) vv[i] = INF - dv[i];
    s=0; t=0;
    cout << "? 1 " << s << " " << t << endl;
    cout.flush();
    dist11.resize(kk);
    for(int i=0; i<kk; i++) cin >> dist11[i];
    s=0; t=MAXC;
    cout << "? 1 " << s << " " << t << endl;
    cout.flush();
    dist22.resize(kk);
    for(int i=0; i<kk; i++) cin >> dist22[i];
    p1 = 0; q1 = 0;
    p2 = MAXC; q2 = -MAXC;
    vector<bool> used(kk, false);
    vector<int> pairing(kk, -1);
    multiset<ll> rem1;
    for(auto x : dist11) rem1.insert(x);
    multiset<ll> rem2;
    for(auto x : dist22) rem2.insert(x);
    recurse(0, used, rem1, rem2, pairing);
    vector<ll> xs(kk), ys(kk);
    for(int i=0; i<kk; i++){
        int j = pairing[i];
        xs[i] = (uu[i] + vv[j]) / 2;
        ys[i] = (uu[i] - vv[j]) / 2;
    }
    cout << "!";
    for(int i=0; i<kk; i++){
        cout << " " << xs[i] << " " << ys[i];
    }
    cout << endl;
    cout.flush();
    return 0;
}