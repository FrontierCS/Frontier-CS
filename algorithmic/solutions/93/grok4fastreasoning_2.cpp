#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n, ty;
  cin >> n >> ty;
  vector<int> gg(n + 1);
  for (int v = 1; v <= n; v++) {
    cout << "? " << n << " " << v;
    for (int i = 1; i <= n; i++) {
      if (i != v) cout << " " << i;
    }
    cout << "\n";
    cout.flush();
    int r;
    cin >> r;
    gg[v] = r - 1;
  }
  int root = -1;
  for (int v = 1; v <= n; v++) {
    if (gg[v] == 0) {
      root = v;
      break;
    }
  }
  vector<int> parent(n + 1, 0);
  parent[root] = 0;
  if (n == 1) {
    cout << "! " << parent[1] << "\n";
    cout.flush();
    return 0;
  }
  vector<int> non_root;
  for (int i = 1; i <= n; i++) {
    if (i != root) non_root.push_back(i);
  }
  auto cmp = [&](int aa, int bb) {
    if (gg[aa] != gg[bb]) return gg[aa] < gg[bb];
    return aa < bb;
  };
  sort(non_root.begin(), non_root.end(), cmp);
  int nnn = non_root.size();
  vector<int> child_pos;
  int cur_size = 0;
  int last_pos = -1;
  if (nnn > 0) {
    child_pos.push_back(0);
    cur_size = 1;
    last_pos = 0;
  }
  while (true) {
    int l = last_pos + 1;
    int r = nnn - 1;
    if (l > r) break;
    int min_pos = -1;
    while (l <= r) {
      int md = (l + r) / 2;
      cout << "? " << (md + 1);
      for (int j = 0; j <= md; j++) {
        cout << " " << non_root[j];
      }
      cout << "\n";
      cout.flush();
      int rr;
      cin >> rr;
      if (rr >= cur_size + 1) {
        min_pos = md;
        r = md - 1;
      } else {
        l = md + 1;
      }
    }
    if (min_pos == -1) break;
    child_pos.push_back(min_pos);
    last_pos = min_pos;
    cur_size++;
  }
  vector<int> children;
  for (auto p : child_pos) children.push_back(non_root[p]);
  int kk = children.size();
  for (auto c : children) parent[c] = root;
  vector<bool> is_child(n + 1, false);
  for (auto c : children) is_child[c] = true;
  vector<int> remain;
  for (auto z : non_root) {
    if (!is_child[z]) remain.push_back(z);
  }
  int mm = remain.size();
  vector<vector<int>> assign(kk);
  for (int ii = 0; ii < mm; ii++) {
    int x = remain[ii];
    int low = 0, high = kk - 1;
    while (low < high) {
      int mid = (low + high) / 2;
      int ssz = mid - low + 1;
      cout << "? " << (ssz + 1);
      for (int j = low; j <= mid; j++) {
        cout << " " << children[j];
      }
      cout << " " << x << "\n";
      cout.flush();
      int rr;
      cin >> rr;
      if (rr == ssz) {
        high = mid;
      } else {
        low = mid + 1;
      }
    }
    assign[low].push_back(x);
  }
  auto rec = [&](auto&& self, vector<int> nodelist, int uu) -> void {
    int sss = nodelist.size();
    if (sss == 1) return;
    vector<int> pdesc;
    for (auto nd : nodelist) {
      if (nd != uu) pdesc.push_back(nd);
    }
    int pnnn = pdesc.size();
    sort(pdesc.begin(), pdesc.end(), cmp);
    vector<int> sub_c_pos;
    int cur_s2 = 0;
    int last_p2 = -1;
    if (pnnn > 0) {
      sub_c_pos.push_back(0);
      cur_s2 = 1;
      last_p2 = 0;
    }
    while (true) {
      int ll = last_p2 + 1;
      int rr = pnnn - 1;
      if (ll > rr) break;
      int min_p2 = -1;
      while (ll <= rr) {
        int mdd = (ll + rr) / 2;
        cout << "? " << (mdd + 1);
        for (int j = 0; j <= mdd; j++) {
          cout << " " << pdesc[j];
        }
        cout << "\n";
        cout.flush();
        int rrr;
        cin >> rrr;
        if (rrr >= cur_s2 + 1) {
          min_p2 = mdd;
          rr = mdd - 1;
        } else {
          ll = mdd + 1;
        }
      }
      if (min_p2 == -1) break;
      sub_c_pos.push_back(min_p2);
      last_p2 = min_p2;
      cur_s2++;
    }
    vector<int> sub_children;
    for (auto pp : sub_c_pos) sub_children.push_back(pdesc[pp]);
    int kkk = sub_children.size();
    for (auto ddd : sub_children) parent[ddd] = uu;
    vector<bool> is_s_c(n + 1, false);
    for (auto ddd : sub_children) is_s_c[ddd] = true;
    vector<int> s_remain;
    for (auto w : pdesc) {
      if (!is_s_c[w]) s_remain.push_back(w);
    }
    int mmm = s_remain.size();
    vector<vector<int>> s_assign(kkk);
    for (int jjj = 0; jjj < mmm; jjj++) {
      int xxx = s_remain[jjj];
      int looo = 0, hiii = kkk - 1;
      while (looo < hiii) {
        int mddd = (looo + hiii) / 2;
        int ssszz = mddd - looo + 1;
        cout << "? " << (ssszz + 1);
        for (int jjjj = looo; jjjj <= mddd; jjjj++) {
          cout << " " << sub_children[jjjj];
        }
        cout << " " << xxx << "\n";
        cout.flush();
        int rrrr;
        cin >> rrrr;
        if (rrrr == ssszz) {
          hiii = mddd;
        } else {
          looo = mddd + 1;
        }
      }
      s_assign[looo].push_back(xxx);
    }
    for (int jjj = 0; jjj < kkk; jjj++) {
      int ddd = sub_children[jjj];
      vector<int> s_s_list;
      s_s_list.push_back(ddd);
      for (auto dddd : s_assign[jjj]) s_s_list.push_back(dddd);
      self(self, s_s_list, ddd);
    }
  };
  for (int i = 0; i < kk; i++) {
    vector<int> s_list;
    s_list.push_back(children[i]);
    for (auto d : assign[i]) s_list.push_back(d);
    rec(rec, s_list, children[i]);
  }
  cout << "!";
  for (int i = 1; i <= n; i++) {
    cout << " " << parent[i];
  }
  cout << "\n";
  cout.flush();
  return 0;
}