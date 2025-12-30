#include <bits/stdc++.h>
using namespace std;

int main() {
  int si, sj, ti, tj;
  double p;
  cin >> si >> sj >> ti >> tj >> p;
  vector<string> hh(20);
  for(int i=0; i<20; i++) cin >> hh[i];
  vector<string> vv(19);
  for(int i=0; i<19; i++) cin >> vv[i];
  int distt[20][20];
  memset(distt, -1, sizeof(distt));
  queue<pair<int,int>> qq;
  qq.push({ti, tj});
  distt[ti][tj] = 0;
  int ddi[4] = {-1,1,0,0};
  int ddj[4] = {0,0,-1,1};
  while(!qq.empty()) {
    auto [i,j] = qq.front(); qq.pop();
    for(int dd=0; dd<4; dd++) {
      int ni = i + ddi[dd];
      int nj = j + ddj[dd];
      if(ni<0 || ni>19 || nj<0 || nj>19) continue;
      bool can = false;
      int diii = ddi[dd], djjj = ddj[dd];
      if(diii == 1) {
        can = (vv[i][j] == '0');
      } else if(diii == -1) {
        can = (vv[ni][j] == '0');
      } else if(djjj == 1) {
        can = (hh[i][j] == '0');
      } else if(djjj == -1) {
        can = (hh[i][nj] == '0');
      }
      if(can && distt[ni][nj] == -1) {
        distt[ni][nj] = distt[i][j] + 1;
        qq.push({ni,nj});
      }
    }
  }
  string seq = "";
  double curr[20][20];
  memset(curr, 0, sizeof(curr));
  curr[si][sj] = 1.0;
  int m = 0;
  const double EPS = 1e-10;
  while(m < 200) {
    double sumc = 0;
    for(int i=0;i<20;i++) for(int j=0;j<20;j++) sumc += curr[i][j];
    if(sumc < EPS) break;
    double best_reach = -1;
    double best_expd = 1e9;
    char best_ch = 'U';
    for(char ch : {'U','D','L','R'}) {
      double treach = 0;
      double expd_num = 0;
      double tcont = 0;
      int dii=0, djj=0;
      if(ch=='U') dii=-1;
      else if(ch=='D') dii=1;
      else if(ch=='L') djj=-1;
      else if(ch=='R') djj=1;
      for(int i=0; i<20; i++) {
        for(int jj=0; jj<20; jj++) {
          double pr = curr[i][jj];
          if(pr < EPS) continue;
          int ni = i, nj = jj;
          double pb = p * pr;
          if(ni == ti && nj == tj) {
            treach += pb;
          } else {
            expd_num += pb * distt[ni][nj];
            tcont += pb;
          }
          int nni = i + dii, nnj = jj + djj;
          int mi = i, mj = jj;
          bool inbounds = (nni>=0 && nni<20 && nnj>=0 && nnj<20);
          if(inbounds) {
            bool nowall = false;
            if(dii==1) nowall = (vv[i][jj]=='0');
            else if(dii==-1) nowall = (vv[nni][jj]=='0');
            else if(djj==1) nowall = (hh[i][jj]=='0');
            else if(djj==-1) nowall = (hh[i][nnj]=='0');
            if(nowall) {
              mi = nni;
              mj = nnj;
            }
          }
          double pq = (1-p) * pr;
          if(mi == ti && mj == tj) {
            treach += pq;
          } else {
            expd_num += pq * distt[mi][mj];
            tcont += pq;
          }
        }
      }
      double expdd = (tcont > EPS) ? expd_num / tcont : 0.0;
      bool better = false;
      if(treach > best_reach + EPS) {
        better = true;
      } else if( fabs(treach - best_reach) < EPS ) {
        if(expdd < best_expd - EPS) {
          better = true;
        }
      }
      if(better) {
        best_reach = treach;
        best_expd = expdd;
        best_ch = ch;
      }
    }
    seq += best_ch;
    m++;
    double nextt[20][20];
    memset(nextt, 0, sizeof(nextt));
    int dii=0, djj=0;
    if(best_ch=='U') dii=-1;
    else if(best_ch=='D') dii=1;
    else if(best_ch=='L') djj=-1;
    else if(best_ch=='R') djj=1;
    for(int i=0; i<20; i++) {
      for(int jj=0; jj<20; jj++) {
        double pr = curr[i][jj];
        if(pr < EPS) continue;
        int ni = i, nj = jj;
        if(ni != ti || nj != tj) {
          nextt[ni][nj] += p * pr;
        }
        int nni = i + dii, nnj = jj + djj;
        int mi = i, mj = jj;
        bool inbounds = (nni>=0 && nni<20 && nnj>=0 && nnj<20);
        if(inbounds) {
          bool nowall = false;
          if(dii==1) nowall = (vv[i][jj]=='0');
          else if(dii==-1) nowall = (vv[nni][jj]=='0');
          else if(djj==1) nowall = (hh[i][jj]=='0');
          else if(djj==-1) nowall = (hh[i][nnj]=='0');
          if(nowall) {
            mi = nni;
            mj = nnj;
          }
        }
        if(mi != ti || mj != tj) {
          nextt[mi][mj] += (1-p) * pr;
        }
      }
    }
    memcpy(curr, nextt, sizeof(nextt));
  }
  cout << seq << endl;
  return 0;
}