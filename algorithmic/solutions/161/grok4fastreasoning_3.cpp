#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
const ll INF = 1LL<<60;

struct Edge {
  int u,v,w,id;
};

bool cmp(const Edge& a, const Edge& b){ return a.w < b.w; }

int par[105];
int find(int x){
  return par[x]==x ? x : par[x]=find(par[x]);
}
void unite(int a, int b){
  a=find(a); b=find(b);
  if(a!=b) par[a]=b;
}

int main(){
  ios::sync_with_stdio(false);
  cin.tie(0);
  int N,M,K;
  cin>>N>>M>>K;
  vector<int> X(N+1), Y(N+1);
  for(int i=1;i<=N;i++){
    cin>>X[i]>>Y[i];
  }
  vector<int> U(M), V(M), W(M);
  vector<Edge> edges;
  for(int j=0;j<M;j++){
    int u,v,w;
    cin>>u>>v>>w;
    U[j]=u; V[j]=v; W[j]=w;
    edges.push_back({u,v,w,j});
  }
  vector<int> A(K+1), B(K+1);
  for(int k=1;k<=K;k++){
    cin>>A[k]>>B[k];
  }
  // Kruskal
  for(int i=1;i<=N;i++) par[i]=i;
  sort(edges.begin(), edges.end(), cmp);
  vector<int> BB(M,0);
  vector<vector<pair<int,int>>> tree(N+1);
  int compo = N;
  for(auto &e : edges){
    int pu = find(e.u), pv = find(e.v);
    if(pu == pv) continue;
    unite(e.u, e.v);
    BB[e.id] = 1;
    tree[e.u].emplace_back(e.v, e.id);
    tree[e.v].emplace_back(e.u, e.id);
    compo--;
    if(compo==1) break;
  }
  // now coverage
  vector<ll> maxsq(N+1, 0);
  for(int k=1; k<=K; k++){
    ll mind2 = INF;
    int best = -1;
    for(int i=1; i<=N; i++){
      ll dx = X[i] - A[k];
      ll dy = Y[i] - B[k];
      ll d2 = dx*dx + dy*dy;
      if(d2 < mind2){
        mind2 = d2;
        best = i;
      }
    }
    maxsq[best] = max( maxsq[best], mind2 );
  }
  vector<bool> needed(N+1, false);
  for(int i=1;i<=N;i++){
    if(maxsq[i] > 0) needed[i]=true;
  }
  // compute keep
  vector<bool> keep(N+1, false);
  function<bool(int,int)> compute_keep = [&](int node, int pnode) -> bool {
    keep[node] = needed[node];
    for(auto [nei, eid] : tree[node]){
      if(nei == pnode) continue;
      bool sub = compute_keep(nei, node);
      keep[node] |= sub;
    }
    return keep[node];
  };
  compute_keep(1, -1);
  // now prune B
  for(int j=0; j<M; j++){
    if(BB[j] == 0) continue;
    int u=U[j], v=V[j];
    if( !keep[u] || !keep[v] ){
      BB[j] = 0;
    }
  }
  // now P
  auto get_p = [](ll dsq) -> int {
    if(dsq == 0) return 0;
    int low = 0, high = 5001;
    while(low < high){
      int mid = (low + high)/2;
      if( (ll)mid * mid >= dsq ){
        high = mid;
      } else {
        low = mid + 1;
      }
    }
    return min(low, 5000);
  };
  vector<int> PP(N+1, 0);
  for(int i=1; i<=N; i++){
    PP[i] = get_p( maxsq[i] );
  }
  // output
  for(int i=1; i<=N; i++){
    cout << PP[i];
    if(i < N) cout << " ";
    else cout << "\n";
  }
  for(int j=0; j<M; j++){
    cout << BB[j];
    if(j < M-1) cout << " ";
    else cout << "\n";
  }
  return 0;
}