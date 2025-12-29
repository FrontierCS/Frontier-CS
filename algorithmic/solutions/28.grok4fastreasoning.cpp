#include <bits/stdc++.h>
using namespace std;

int main() {
  int T;
  cin >> T;
  for (int t = 0; t < T; t++) {
    int N;
    cin >> N;
    set<string> dictionary;
    for (char ch = 'a'; ch <= 'z'; ch++) {
      string prefix(1, ch);
      cout << "query " << prefix << " 1" << endl;
      cout.flush();
      int obtained;
      cin >> obtained;
      if (obtained == 0) continue;
      vector<string> subtree(obtained);
      for (int i = 0; i < obtained; i++) {
        cin >> subtree[i];
      }
      int current = obtained;
      int ask = 2;
      while (true) {
        cout << "query " << prefix << " " << ask << endl;
        cout.flush();
        int kk;
        cin >> kk;
        vector<string> batch(kk);
        for (int i = 0; i < kk; i++) {
          cin >> batch[i];
        }
        for (int i = current; i < kk; i++) {
          subtree.push_back(batch[i]);
        }
        current = kk;
        if (kk < ask) break;
        ask *= 2;
        if (ask > N) ask = N;
      }
      for (auto& w : subtree) {
        dictionary.insert(w);
      }
    }
    cout << "answer";
    for (auto& w : dictionary) {
      cout << " " << w;
    }
    cout << endl;
    cout.flush();
  }
  return 0;
}