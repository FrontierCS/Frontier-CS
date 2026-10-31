#include <cmath>
#include <algorithm>

// Natural-log calibration above the previous 60-point threshold.
// Keep validation and low scores; an exact zero minimization cost earns 100.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0 || !(value > 0.0L) || !(anchor > 0.0L))
        return old_points;
    const long double delta = minimize ? std::log(anchor) - std::log(value)
                                       : std::log(value) - std::log(anchor);
    return (double)std::min(100.0L, 60.0L + delta);
}

#include "testlib.h"

// Continuous reference calibration; the performance anchor earns 60 points.
static double referenceScore(double r) {
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <set>

using namespace std;

string s[30][1010];
char current[15];
int num[30];
int cnt = 0;
map<string, int>vis;
set<string>dict;

void dfs(int now, int start){
  if(cnt >= 1000)return;
  if(now >= 10){
    cnt++;
    for(int i = 0; i < 10; i++){
      s[start][cnt] += current[i];
    }
    return;
  }
  if(now == 0){
    current[now] = (char)('a'+start);
    dfs(now+1, start);
  }
  else{
    for(int i = 0; i < 26; i++){
      current[now] = (char)('a'+i);
      dfs(now+1, start);
    }
  }
}

int main(int argc, char *argv[]) {
  /*
   * inf: input
   * ouf: contestant output
   * ans: standard output
   */
  registerInteraction(argc, argv);

  for(int i = 0; i < 26; i++){
    cnt = 0;
    dfs(0, i);
  }
  int t = inf.readInt(), n = inf.readInt();
  for(int i = 0; i < 26; i++){
    num[i] = inf.readInt();
    for(int j = 1; j <= num[i]; j++)dict.insert(s[i][j]);
  }
  ensuref((int)dict.size() == n, "The word lists hold %d words, but N is %d", (int)dict.size(), n);
  cout<<t<<endl;
  cout.flush();
  cout<<n<<endl;
  cout.flush();
  int sumk = 0;
  for(int i = 1; i <= 4000; i++){
    string operation = ouf.readWord();
    if(operation == "query"){
      string qs = ouf.readWord();
      if(qs.length() >= 10)quitf(_wa, "Invalid query");
      int k = ouf.readInt(1, n);
      sumk += k;
      int start = qs[0]-'a';
      // Every word starts with a lowercase letter, so other prefixes match nothing.
      int limit = (qs[0] >= 'a' && qs[0] <= 'z') ? num[start] : 0;

      int match_cnt = 0;
      string ret[1010];
      for(int j = 1; j <= limit; j++){
        int match = 1;
        for(int t = 0; t < qs.length(); t++){
          if(s[start][j][t] != qs[t])match = 0;
        }
        if(match){
          match_cnt++;
          ret[match_cnt] = s[start][j];
          if(match_cnt == k)break;
        }
      }
      cout<<match_cnt<<" ";
      for(int j = 1; j <= match_cnt; j++){
        cout<<ret[j]<<" ";
      }
      cout<<endl;
      cout.flush();
    }
    else if(operation == "answer"){
      // n distinct dictionary words are the whole dictionary.
      for(int j = 1; j <= n; j++){
        string answers = ouf.readWord();
        if(!dict.count(answers))quitf(_wa, "Invalid answer");
        if(vis[answers])quitf(_wa, "Repeated answer");
        vis[answers] = 1;
      }
      double score = (4000.0-1.0*sumk)/(4000.0-2400.0);
      score = referenceScore(max(0.0, score));
    score = natural_log_score(100.0 * score, sumk, 2400, true) / 100.0;
      double unbounded_score = score;
      quitp(score, "Ratio: %.12f, RatioUnbounded: %.12f", score, unbounded_score);
    }
    else{
      quitf(_wa, "Invalid operation");
    }
  }
  quitf(_wa, "Too many queries");
}
