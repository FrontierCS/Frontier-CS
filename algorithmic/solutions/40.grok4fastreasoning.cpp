#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  int fixed = 1;
  int l = 2, r = n;
  while (l < r) {
    int size = r - l + 1;
    int mm = min(499, size / 2);
    int tr = l + mm - 1;
    vector<int> tseq;
    tseq.push_back(fixed);
    for (int p = l; p <= tr; p++) {
      tseq.push_back(p);
      tseq.push_back(fixed);
    }
    int kk = tseq.size();
    cout << "0 " << kk;
    for (int id : tseq) cout << " " << id;
    cout << endl;
    cout.flush();
    int resp;
    cin >> resp;
    if (resp > 0) {
      r = tr;
    } else {
      l = tr + 1;
    }
  }
  int j = l;
  cout << "0 2 " << fixed << " " << j << endl;
  cout.flush();
  int resp;
  cin >> resp;
  int open_p, close_p;
  if (resp == 1) {
    open_p = fixed;
    close_p = j;
  } else {
    open_p = j;
    close_p = fixed;
  }
  string ss(n + 1, ' ');
  ss[open_p] = '(';
  ss[close_p] = ')';
  vector<int> remains;
  for (int i = 1; i <= n; i++) {
    if (ss[i] == ' ') remains.push_back(i);
  }
  int posi = 0;
  while (posi < remains.size()) {
    int gs = min(9, (int)remains.size() - posi);
    vector<int> grp;
    for (int ii = 0; ii < gs; ii++) grp.push_back(remains[posi + ii]);
    vector<int> qseq;
    for (int b = 0; b < gs; b++) {
      int mmm = 1 << b;
      for (int tt = 0; tt < mmm; tt++) {
        qseq.push_back(grp[b]);
        qseq.push_back(close_p);
      }
      qseq.push_back(close_p);
    }
    int kkk = qseq.size();
    cout << "0 " << kkk;
    for (int id : qseq) cout << " " << id;
    cout << endl;
    cout.flush();
    int fff;
    cin >> fff;
    int cur = fff;
    for (int b = gs - 1; b >= 0; b--) {
      int mmm = 1 << b;
      int con = mmm * (mmm + 1) / 2;
      if (cur >= con) {
        ss[grp[b]] = '(';
        cur -= con;
      } else {
        ss[grp[b]] = ')';
      }
    }
    posi += gs;
  }
  cout << "1";
  for (int i = 1; i <= n; i++) cout << ss[i];
  cout << endl;
  cout.flush();
  return 0;
}