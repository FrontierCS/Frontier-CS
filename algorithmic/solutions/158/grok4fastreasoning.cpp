#include <bits/stdc++.h>
using namespace std;
using ll = long long;
int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int N, K;
  cin >> N >> K;
  vector<int> a(11,0);
  for(int d=1; d<=10; d++) cin >> a[d];
  vector<pair<ll,ll>> points(N);
  vector<ll> all_x(N), all_y(N);
  for(int i=0; i<N; i++){
    ll x,y;
    cin >> x >> y;
    points[i] = {x,y};
    all_x[i] = x;
    all_y[i] = y;
  }
  auto get_cuts = [&](const vector<ll>& sorted_coords, int target_num) -> vector<ll> {
    if(N==0) return {};
    set<ll> ux_set(sorted_coords.begin(), sorted_coords.end());
    vector<ll> unique_x(ux_set.begin(), ux_set.end());
    int nu = unique_x.size();
    if(nu < 2) return {};
    map<ll, int> count_x;
    for(auto xx : sorted_coords) count_x[xx]++;
    vector<int> pref(nu+1, 0);
    for(int i=1; i<=nu; i++){
      pref[i] = pref[i-1] + count_x[unique_x[i-1]];
    }
    vector<ll> cuts;
    int groups = target_num + 1;
    for(int ii=1; ii<=target_num; ii++){
      int target_left = (ll)ii * N / groups;
      int j = -1;
      for(int kk=0; kk<nu-1; kk++){
        if(pref[kk+1] >= target_left){
          j = kk;
          break;
        }
      }
      if(j == -1 || j >= nu-1) continue;
      ll left = unique_x[j];
      ll rght = unique_x[j+1];
      bool placed = false;
      if(rght > left + 1){
        cuts.push_back(left + 1);
        placed = true;
      } else {
        for(int kk=j; kk<nu-1; kk++){
          ll l = unique_x[kk];
          ll r = unique_x[kk+1];
          if(r > l + 1){
            cuts.push_back(l + 1);
            placed = true;
            break;
          }
        }
      }
      if(!placed) continue;
    }
    sort(cuts.begin(), cuts.end());
    auto it = unique(cuts.begin(), cuts.end());
    cuts.resize(it - cuts.begin());
    return cuts;
  };
  int best_score = -1;
  vector<ll> best_cx, best_cy;
  for(int vt=0; vt<=K; vt++){
    vector<ll> cx = get_cuts(all_x, vt);
    int av = cx.size();
    int ht = K - vt;
    vector<ll> cy = get_cuts(all_y, ht);
    int ah = cy.size();
    auto get_sx = [&](ll xp) -> int {
      auto it = upper_bound(cx.begin(), cx.end(), xp);
      return it - cx.begin();
    };
    auto get_sy = [&](ll yp) -> int {
      auto it = upper_bound(cy.begin(), cy.end(), yp);
      return it - cy.begin();
    };
    int msx = av + 1;
    int msy = ah + 1;
    vector<vector<int>> freq(msx, vector<int>(msy, 0));
    for(int i=0; i<N; i++){
      ll xp = points[i].first;
      ll yp = points[i].second;
      int sx_ = get_sx(xp);
      int sy_ = get_sy(yp);
      freq[sx_][sy_]++;
    }
    vector<int> bb(11,0);
    for(int i=0; i<msx; i++){
      for(int j=0; j<msy; j++){
        int c = freq[i][j];
        if(c > 0 && c <=10) bb[c]++;
      }
    }
    int sc = 0;
    for(int d=1; d<=10; d++){
      sc += min(a[d], bb[d]);
    }
    if(sc > best_score){
      best_score = sc;
      best_cx = cx;
      best_cy = cy;
    }
  }
  vector<tuple<ll,ll,ll,ll>> lines;
  ll INF = 1000000000LL;
  for(auto m : best_cx){
    lines.emplace_back(m, -INF, m, INF);
  }
  for(auto n : best_cy){
    lines.emplace_back(-INF, n, INF, n);
  }
  cout << lines.size() << '\n';
  for(auto [px,py,qx,qy] : lines){
    cout << px << ' ' << py << ' ' << qx << ' ' << qy << '\n';
  }
  return 0;
}