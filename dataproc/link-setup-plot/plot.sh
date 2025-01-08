WORK_DIR=$(dirname $(readlink -f $0))
logfile=$1

python3 ${WORK_DIR}/plot_outlier_profile.py ${logfile}
# python3 ${WORK_DIR}/plot_outlier_profile.py ${logfile} --outlier-tolerance-offset-ratio 1 --window 100
python3 ${WORK_DIR}/plot_outlier_profile.py ${logfile} --outlier-tolerance-offset-ratio 1 --window 200
# python3 ${WORK_DIR}/plot_outlier_profile.py ${logfile} --outlier-tolerance-offset-ratio 2 --window 100
# python3 ${WORK_DIR}/plot_outlier_profile.py ${logfile} --outlier-tolerance-offset-ratio 2 --window 200

python3 ${WORK_DIR}/plot_outlier_acc_time.py ${logfile}
# python3 ${WORK_DIR}/plot_outlier_acc_time.py ${logfile} --outlier-tolerance-offset-ratio 1 --window 100
python3 ${WORK_DIR}/plot_outlier_acc_time.py ${logfile} --outlier-tolerance-offset-ratio 1 --window 200
# python3 ${WORK_DIR}/plot_outlier_acc_time.py ${logfile} --outlier-tolerance-offset-ratio 2 --window 100
# python3 ${WORK_DIR}/plot_outlier_acc_time.py ${logfile} --outlier-tolerance-offset-ratio 2 --window 200

cd - > /dev/null
