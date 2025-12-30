#include <bits/stdc++.h>
using namespace std;

int main() {
  int T;
  cin >> T;
  for(int t = 0; t < T; t++) {
    int N;
    cin >> N;
    vector<string> all_words;
    int discovered = 0;
    for(char ch = 'a'; ch <= 'z'; ch++) {
      string prefix = "";
      prefix += ch;
      cout << "query " << prefix << " 1" << endl;
      cout.flush();
      int k;
      cin >> k;
      vector<string> res(k);
      for(int i = 0; i < k; i++) {
        cin >> res[i];
      }
      if(k == 0) continue;
      int d_before = discovered;
      int r_max = N - d_before;
      discovered += k;
      for(auto& w : res) {
        all_words.push_back(w);
      }
      int current_max = k;
      while(true) {
        long long next_k_ll = (long long) current_max * 2;
        next_k_ll = min(next_k_ll, (long long) r_max);
        int next_k = (int) next_k_ll;
        if(next_k <= current_max) break;
        cout << "query " << prefix << " " << next_k << endl;
        cout.flush();
        int num;
        cin >> num;
        vector<string> newres(num);
        for(int i = 0; i < num; i++) {
          cin >> newres[i];
        }
        int newc = 0;
        for(int i = current_max; i < num; i++) {
          all_words.push_back(newres[i]);
          newc++;
        }
        discovered += newc;
        if(num < next_k || next_k == r_max) {
          break;
        }
        current_max = next_k;
      }
    }
    cout << "answer";
    for(auto& w : all_words) {
      cout << " " << w;
    }
    cout << endl;
    cout.flush();
  }
  return 0;
}