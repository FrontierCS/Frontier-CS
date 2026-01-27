#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int t;
  cin >> t;
  for (int tt = 0; tt < t; tt++) {
    int n;
    cin >> n;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; i++) {
      int u, v;
      cin >> u >> v;
      adj[u].push_back(v);
      adj[v].push_back(u);
    }
    // query all
    vector<int> alll(n);
    iota(alll.begin(), alll.end(), 1);
    cout << "? " << n;
    for (int nd : alll) cout << " " << nd;
    cout << endl;
    cout.flush();
    int x0, D;
    cin >> x0 >> D;
    if (x0 == -1) return 0;
    // BFS from x0
    vector<int> dist(n + 1, -1);
    queue<int> qq;
    qq.push(x0);
    dist[x0] = 0;
    while (!qq.empty()) {
      int u = qq.front();
      qq.pop();
      for (int v : adj[u]) {
        if (dist[v] == -1) {
          dist[v] = dist[u] + 1;
          qq.push(v);
        }
      }
    }
    // childs
    vector<int> childs;
    for (int v : adj[x0]) childs.push_back(v);
    int mm = childs.size();
    // subtrees
    vector<vector<int>> subtrees(mm);
    auto collect = [&](auto&& self, int u, int p, int idxx) -> void {
      subtrees[idxx].push_back(u);
      for (int v : adj[u]) {
        if (v != p && dist[v] == dist[u] + 1) {
          self(self, v, u, idxx);
        }
      }
    };
    for (int i = 0; i < mm; i++) {
      int c = childs[i];
      collect(collect, c, x0, i);
    }
    // do_query
    auto do_query = [&](const vector<int>& qset) -> pair<int, int> {
      int szz = qset.size();
      cout << "? " << szz;
      for (int nd : qset) cout << " " << nd;
      cout << endl;
      cout.flush();
      int xxd, ddd;
      cin >> xxd >> ddd;
      if (xxd == -1) exit(0);
      return {xxd, ddd};
    };
    // has_special
    auto has_special = [&](int lft, int rgt) -> bool {
      if (lft > rgt) return false;
      vector<int> qset;
      for (int ii = lft; ii <= rgt; ii++) {
        qset.insert(qset.end(), subtrees[ii].begin(), subtrees[ii].end());
      }
      auto [xx, dd] = do_query(qset);
      return (dd == D);
    };
    // find i1
    int i1 = -1;
    {
      int loo = 0, hii = mm;
      while (loo < hii) {
        int midd = (loo + hii) / 2;
        bool hass = has_special(0, midd);
        if (hass) {
          hii = midd;
        } else {
          loo = midd + 1;
        }
      }
      if (loo < mm) {
        i1 = loo;
      }
    }
    vector<int> special_idx;
    if (i1 != -1) {
      special_idx.push_back(i1);
      // find i2
      int i2 = -1;
      {
        int startt = i1 + 1;
        int enddd = mm - 1;
        if (startt <= enddd) {
          int loo = startt, hii = enddd + 1;
          while (loo < hii) {
            int midd = (loo + hii) / 2;
            bool hass = has_special(startt, midd);
            if (hass) {
              hii = midd;
            } else {
              loo = midd + 1;
            }
          }
          if (loo <= enddd) {
            i2 = loo;
          }
        }
      }
      if (i2 != -1) special_idx.push_back(i2);
    }
    // find ends
    vector<int> hidden;
    auto find_end_node = [&](int idxx) -> int {
      vector<int> stt = subtrees[idxx];
      int hhh = 0;
      for (int v : stt) hhh = max(hhh, dist[v]);
      int loo = 1, hii = hhh;
      int maxkk = 0;
      while (loo <= hii) {
        int md = (loo + hii) / 2;
        vector<int> AA;
        for (int v : stt)
          if (dist[v] == md) AA.push_back(v);
        if (AA.empty()) {
          hii = md - 1;
          continue;
        }
        auto [xxd, ddd] = do_query(AA);
        if (ddd == D) {
          maxkk = md;
          loo = md + 1;
        } else {
          hii = md - 1;
        }
      }
      int aa = maxkk;
      vector<int> AA;
      for (int v : stt)
        if (dist[v] == aa) AA.push_back(v);
      auto [xxd, ddd] = do_query(AA);
      return xxd;
    };
    if (special_idx.empty()) {
      hidden = {x0, x0};
    } else if (special_idx.size() == 1) {
      int idxx = special_idx[0];
      int ee = find_end_node(idxx);
      hidden = {x0, ee};
    } else {
      int idxx1 = special_idx[0];
      int e1 = find_end_node(idxx1);
      int idxx2 = special_idx[1];
      int e2 = find_end_node(idxx2);
      hidden = {e1, e2};
    }
    // output
    cout << "! " << hidden[0] << " " << hidden[1] << endl;
    cout.flush();
    string verdict;
    cin >> verdict;
    if (verdict == "Incorrect") return 0;
  }
  return 0;
}