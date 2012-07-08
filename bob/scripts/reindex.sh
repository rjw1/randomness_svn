#!/bin/bash
# script to reindex an openguides install on nimbus

while getopts "u:s:h" option
do
  case $option in
   u ) SITEUSER=$OPTARG ;;
   s ) SITE=$OPTARG ;;
   h ) HELP=1 ;;
   * ) HELP=1 ;;
  esac
done

if [[ -z $SITEUSER ]]
then
	echo "no site user set"
	HELP=1
fi
if [[ -z $SITE ]]
then
	echo "no site user set"
	HELP=1
fi
if [ "$HELP" = "1" ]
then
  echo "reindex a site"
  echo "-s site (e.g. dev.croydon.randomness.org.uk)"
  echo "-u site user (e.g. rgc)"
  echo "-h this help message"
  exit 0
fi
STARTEPOCH=$(date +'%s')
APPNAME=$(basename $0)

SITEDIR="/export/home/$SITEUSER/web/vhosts/$SITE"
INDEXDIR="$SITEDIR/indexes"
USERLIB=/export/home/$SITEUSER/perl5/lib/perl5/
SITELIB=$SITEDIR/scripts/lib/
if [ ! -d "$SITEDIR" ]; then
  echo "$APPNAME: The directory $SITEDIR doesnt exist for $SITE"
  exit 1
fi

echo "enabling holding page for $SITE"
touch $SITEDIR/holding.enable

echo "removing current indexes : $INDEXDIR"
rm -rf $INDEXDIR/*

echo "reindexing $SITE"
cd $SITEDIR
perl -I $SITELIB -I $USERLIB ~rgl/bin/reindex.pl

echo  "changing ownership of indexes"
chown -R www-data\: $INDEXDIR

FINISHEPOCH=$(date +'%s')

TOTALTIME=$(expr $FINISHEPOCH - $STARTEPOCH)

MESSAGE="Reindexed $SITE in $TOTALTIME seconds"
echo $MESSAGE
logger -i -p local0.notice -t $APPNAME $MESSAGE

 
