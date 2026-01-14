#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  if (n == 0) return 0;
  vector<vector<int>> groups;
  int cur = 1;
  while (cur <= n) {
    vector<int> gp;
    for (int j = 0; j < 3 && cur <= n; j++, cur++) {
      gp.push_back(cur);
    }
    groups.push_back(gp);
  }
  int num_g = groups.size();
  vector<vector<int>> pos_by_rank(num_g, vector<int>(4, 0));
  for (int g = 0; g < num_g; g++) {
    auto& gp = groups[g];
    int ss = gp.size();
    if (ss == 1) {
      pos_by_rank[g][1] = gp[0];
      continue;
    }
    if (ss == 2) {
      int p1 = gp[0], p2 = gp[1];
      cout << "? " << p1 << " " << p2 << endl;
      cout.flush();
      char res;
      cin >> res;
      int num0 = (res == '>') ? 1 : 0;
      int rank0 = 1 + num0;
      int num1 = (res == '<') ? 1 : 0;
      int rank1 = 1 + num1;
      if (rank0 == 1) {
        pos_by_rank[g][1] = p1;
        pos_by_rank[g][2] = p2;
      } else {
        pos_by_rank[g][1] = p2;
        pos_by_rank[g][2] = p1;
      }
      continue;
    }
    // ss == 3
    int p0 = gp[0], p1 = gp[1], p2 = gp[2];
    cout << "? " << p0 << " " << p1 << endl;
    cout.flush();
    char s01;
    cin >> s01;
    cout << "? " << p0 << " " << p2 << endl;
    cout.flush();
    char s02;
    cin >> s02;
    cout << "? " << p1 << " " << p2 << endl;
    cout.flush();
    char s12;
    cin >> s12;
    int num0 = (s01 == '>') + (s02 == '>');
    int r0 = 1 + num0;
    int num1 = (s01 == '<') + (s12 == '>');
    int r1 = 1 + num1;
    int num2 = (s02 == '<') + (s12 == '<');
    int r2 = 1 + num2;
    pos_by_rank[g][r0] = p0;
    pos_by_rank[g][r1] = p1;
    pos_by_rank[g][r2] = p2;
  }
  vector<char> conn1(num_g - 1);
  vector<char> conn2(num_g - 1, ' ');
  for (int g = 0; g < num_g - 1; g++) {
    int lastp = groups[g].back();
    int n1 = groups[g + 1][0];
    cout << "? " << lastp << " " << n1 << endl;
    cout.flush();
    cin >> conn1[g];
    if (groups[g + 1].size() >= 2) {
      int n2 = groups[g + 1][1];
      cout << "? " << lastp << " " << n2 << endl;
      cout.flush();
      cin >> conn2[g];
    }
  }
  vector<int> aa(n + 1, 0);
  set<int> unasss;
  for (int i = 1; i <= n; i++) unasss.insert(i);
  if (num_g == 1) {
    auto& gp = groups[0];
    int ss = gp.size();
    vector<int> vals;
    auto itt = unasss.begin();
    for (int j = 0; j < ss; j++, ++itt) vals.push_back(*itt);
    for (int r = 1; r <= ss; r++) {
      int pp = pos_by_rank[0][r];
      aa[pp] = vals[r - 1];
    }
  } else {
    // first two
    int sz0 = groups[0].size();
    int max0 = min(n, sz0 + 2);
    vector<int> avail0;
    for (int j = 1; j <= max0; j++) avail0.push_back(j);
    int na0 = avail0.size();
    int sz1 = groups[1].size();
    bool found = false;
    vector<int> the_set0, the_set1;
    for (int msk0 = 0; msk0 < (1 << na0); msk0++) {
      if (__builtin_popcount(msk0) != sz0) continue;
      vector<int> set0;
      for (int b = 0; b < na0; b++)
        if (msk0 & (1 << b)) set0.push_back(avail0[b]);
      vector<int> temp_a0(n + 1, 0);
      for (int r = 1; r <= sz0; r++) {
        int pp = pos_by_rank[0][r];
        temp_a0[pp] = set0[r - 1];
      }
      int val_last0 = temp_a0[groups[0].back()];
      set<int> t_un;
      for (int j = 1; j <= n; j++) t_un.insert(j);
      for (int vv : set0) t_un.erase(vv);
      vector<int> avail1;
      auto ittt = t_un.begin();
      int need1 = min(5, (int)t_un.size());
      for (int j = 0; j < need1; j++, ++ittt) avail1.push_back(*ittt);
      int na1 = avail1.size();
      if (na1 < sz1) continue;
      for (int msk1 = 0; msk1 < (1 << na1); msk1++) {
        if (__builtin_popcount(msk1) != sz1) continue;
        vector<int> set1;
        for (int b = 0; b < na1; b++)
          if (msk1 & (1 << b)) set1.push_back(avail1[b]);
        vector<int> temp_a1(n + 1, 0);
        for (int r = 1; r <= sz1; r++) {
          int pp = pos_by_rank[1][r];
          temp_a1[pp] = set1[r - 1];
        }
        bool okk = true;
        int nn1 = groups[1][0];
        int vnn1 = temp_a1[nn1];
        bool actt = (val_last0 < vnn1);
        char actcc = actt ? '<' : '>';
        if (actcc != conn1[0]) okk = false;
        if (okk && sz1 >= 2 && conn2[0] != ' ') {
          int nn2 = groups[1][1];
          int vnn2 = temp_a1[nn2];
          actt = (val_last0 < vnn2);
          actcc = actt ? '<' : '>';
          if (actcc != conn2[0]) okk = false;
        }
        if (okk) {
          found = true;
          the_set0 = set0;
          the_set1 = set1;
          for (int r = 1; r <= sz0; r++) {
            int pp = pos_by_rank[0][r];
            aa[pp] = set0[r - 1];
          }
          for (int r = 1; r <= sz1; r++) {
            int pp = pos_by_rank[1][r];
            aa[pp] = set1[r - 1];
          }
        }
      }
    }
    for (int vv : the_set0) unasss.erase(vv);
    for (int vv : the_set1) unasss.erase(vv);
    // now remaining groups
    for (int gg = 2; gg < num_g; gg++) {
      vector<int> avail;
      auto it = unasss.begin();
      int need = min(5, (int)unasss.size());
      for (int j = 0; j < need; j++, ++it) avail.push_back(*it);
      int na = avail.size();
      int szz = groups[gg].size();
      bool fnd = false;
      vector<int> ch_set;
      int bnd_idx = gg - 1;
      int prev_end = groups[gg - 1].back();
      int v_prev_end = aa[prev_end];
      for (int msk = 0; msk < (1 << na); msk++) {
        if (__builtin_popcount(msk) != szz) continue;
        vector<int> st;
        for (int b = 0; b < na; b++)
          if (msk & (1 << b)) st.push_back(avail[b]);
        vector<int> t_a(n + 1, 0);
        for (int r = 1; r <= szz; r++) {
          int pp = pos_by_rank[gg][r];
          t_a[pp] = st[r - 1];
        }
        bool ok = true;
        int fnn = groups[gg][0];
        int v_fnn = t_a[fnn];
        bool act = v_prev_end < v_fnn;
        char ac = act ? '<' : '>';
        if (ac != conn1[bnd_idx]) ok = false;
        if (ok && szz >= 2 && conn2[bnd_idx] != ' ') {
          int snn = groups[gg][1];
          int v_snn = t_a[snn];
          act = v_prev_end < v_snn;
          ac = act ? '<' : '>';
          if (ac != conn2[bnd_idx]) ok = false;
        }
        if (ok) {
          fnd = true;
          ch_set = st;
          for (int r = 1; r <= szz; r++) {
            int pp = pos_by_rank[gg][r];
            aa[pp] = st[r - 1];
          }
        }
      }
      for (int vv : ch_set) unasss.erase(vv);
    }
  }
  cout << "!";
  for (int i = 1; i <= n; i++) cout << " " << aa[i];
  cout << endl;
  cout.flush();
  return 0;
}